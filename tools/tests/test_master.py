import os
import tomllib
from pathlib import Path

from gmod2nanos import master


def _toml(title: str, meshes: dict[str, str], folders=("Pack",)) -> dict:
    return {
        "meta": {"title": title, "author": "", "version": "1.0.0"},
        "asset_pack": {"assets_requirements": []},
        "unreal": {"unreal_folders": list(folders), "unreal_version": "5.7.4", "is_plugin_content": False},
        "assets": {"maps": {}, "skeletal_meshes": meshes, "others": {}},
    }


def _pack(root: Path, doc: dict, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "Assets.toml").write_text(master.dump_toml(doc), encoding="utf-8")
    for name, data in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(data)


def test_dump_toml_roundtrip():
    doc = _toml('[YUFU]PM "VAAS"', {"SK_a": "Pack/Characters/SK_a", "SK_é": "Pack/é"})
    doc["asset_pack"]["assets_requirements"] = ["nanos-world"]
    assert tomllib.loads(master.dump_toml(doc)) == doc


def test_merge_toml_keeps_master_meta_and_accumulates_entries():
    base = _toml("[YUFU]PM VAAS", {"SK_old": "Pack/SK_old", "SK_both": "Pack/old"})
    new = _toml("Pack", {"SK_new": "Pack/SK_new", "SK_both": "Pack/new"}, folders=("Pack", "Other"))
    merged = master.merge_toml(base, new)
    assert merged["meta"]["title"] == "[YUFU]PM VAAS"
    assert merged["assets"]["skeletal_meshes"] == {"SK_old": "Pack/SK_old", "SK_both": "Pack/new", "SK_new": "Pack/SK_new"}
    assert merged["unreal"]["unreal_folders"] == ["Pack", "Other"]
    assert base["assets"]["skeletal_meshes"] == {"SK_old": "Pack/SK_old", "SK_both": "Pack/old"}  # base intacte


def test_sync_pack_accumulates_across_cooks(tmp_path: Path):
    cook, mast, server = tmp_path / "cook", tmp_path / "master", tmp_path / "server"
    _pack(server / "pk", _toml("Curated", {"SK_server": "Pack/SK_server"}), {"Pack/SK_server.uasset": b"srv"})
    _pack(cook / "pk", _toml("Pack", {"SK_a": "Pack/SK_a"}), {"Pack/SK_a.uasset": b"a1"})

    master.sync_pack("pk", cook, mast, server, deploy=True, restore=True, log=lambda m: None)

    expected = {"SK_server": "Pack/SK_server", "SK_a": "Pack/SK_a"}
    for root in (mast, server, cook):
        doc = tomllib.loads((root / "pk" / "Assets.toml").read_text(encoding="utf-8"))
        assert doc["meta"]["title"] == "Curated"
        assert doc["assets"]["skeletal_meshes"] == expected
        assert (root / "pk/Pack/SK_server.uasset").read_bytes() == b"srv"
        assert (root / "pk/Pack/SK_a.uasset").read_bytes() == b"a1"

    # seconde cuisson : Forge réécrit Assets.toml sans SK_a, et SK_b est nouveau
    _pack(cook / "pk", _toml("Pack", {"SK_b": "Pack/SK_b"}), {"Pack/SK_b.uasset": b"b1", "Pack/SK_a.uasset": b"a2"})
    later = (cook / "pk/Pack/SK_a.uasset").stat().st_mtime + 60  # une vraie cuisson arrive des minutes plus tard
    os.utime(cook / "pk/Pack/SK_a.uasset", (later, later))
    master.sync_pack("pk", cook, mast, server, deploy=True, restore=True, log=lambda m: None)

    expected["SK_b"] = "Pack/SK_b"
    for root in (mast, server, cook):
        doc = tomllib.loads((root / "pk" / "Assets.toml").read_text(encoding="utf-8"))
        assert doc["assets"]["skeletal_meshes"] == expected
        assert (root / "pk/Pack/SK_a.uasset").read_bytes() == b"a2"
    assert list((mast / "_history" / "pk").glob("cook-*.toml"))  # l'Assets.toml écrasé par Forge est gardé


def test_sync_pack_skips_server_when_not_deployed(tmp_path: Path):
    cook, mast, server = tmp_path / "cook", tmp_path / "master", tmp_path / "server"
    server.mkdir()
    _pack(cook / "pk", _toml("Pack", {"SK_a": "Pack/SK_a"}), {"Pack/SK_a.uasset": b"a"})
    master.sync_pack("pk", cook, mast, server, deploy=False, restore=True, log=lambda m: None)
    assert (mast / "pk/Pack/SK_a.uasset").exists()
    assert not (server / "pk").exists()


def test_sync_pack_publishes_under_alias(tmp_path: Path):
    cook, mast, server = tmp_path / "cook", tmp_path / "master", tmp_path / "server"
    _pack(cook / "raw", _toml("Raw", {"SK_a": "Pack/SK_a"}), {"Pack/SK_a.uasset": b"a"})
    master.sync_pack("raw", cook, mast, server, deploy=True, restore=True, log=lambda m: None, name="pretty")
    for root in (mast, server, cook):
        assert (root / "pretty/Pack/SK_a.uasset").read_bytes() == b"a"
        assert tomllib.loads((root / "pretty/Assets.toml").read_text(encoding="utf-8"))["assets"]["skeletal_meshes"] == {
            "SK_a": "Pack/SK_a"
        }
    assert not (mast / "raw").exists() and not (server / "raw").exists()
    assert master.list_packs(cook) == ["pretty", "raw"]
    assert master.list_packs(cook, {"pretty"}) == ["raw"]


def test_merge_tree_never_deletes_and_skips_identical(tmp_path: Path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    _pack(src, _toml("P", {}), {"x.bin": b"new", "same.bin": b"same"})
    _pack(dst, _toml("P", {}), {"x.bin": b"old!", "same.bin": b"same", "keep.bin": b"keep"})
    os.utime(src / "same.bin", (1_000_000, 1_000_000))
    assert master.merge_tree(src, dst) == 1
    assert (dst / "x.bin").read_bytes() == b"new"
    assert (dst / "keep.bin").read_bytes() == b"keep"
    assert master.merge_tree(src, dst) == 0


def test_snapshot_survives_a_file_vanishing_during_the_cook(tmp_path: Path, monkeypatch):
    _pack(tmp_path / "pk", _toml("P", {}), {"a.bin": b"a", "gone.bin": b"g"})
    real_stat = os.stat

    def flaky_stat(path, *args, **kwargs):
        if str(path).endswith("gone.bin"):
            raise FileNotFoundError(path)
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(master.os, "stat", flaky_stat)
    count = master.snapshot(tmp_path / "pk")[0]
    assert count == 1  # a.bin seulement : Assets.toml est suivi par son contenu, et gone.bin a disparu


def test_snapshot_ignores_toml_reformatting_but_not_content_changes(tmp_path: Path):
    doc = _toml("P", {"SK_a": "Pack/SK_a"})
    _pack(tmp_path / "pk", doc, {"a.bin": b"a"})
    before = master.snapshot(tmp_path / "pk")
    # le serveur nanos réécrit Assets.toml avec des commentaires et une autre indentation : même contenu
    (tmp_path / "pk" / "Assets.toml").write_text(
        '# vault configurations\n[meta]\n    title = "P"\n    author = ""\n    version = "1.0.0"\n\n'
        '[asset_pack]\n    assets_requirements = [\n\n    ]\n\n[unreal]\n    unreal_folders = ["Pack"]\n'
        '    unreal_version = "5.7.4"\n    is_plugin_content = false\n\n[assets]\n    [assets.maps]\n\n'
        '    [assets.skeletal_meshes]\n        SK_a = "Pack/SK_a"\n\n    [assets.others]\n',
        encoding="utf-8")
    assert master.snapshot(tmp_path / "pk") == before
    # une entrée en moins (ce que fait un cook Forge qui oublie d'anciens assets) est bien détectée
    (tmp_path / "pk" / "Assets.toml").write_text(master.dump_toml(_toml("P", {})), encoding="utf-8")
    assert master.snapshot(tmp_path / "pk") != before


def test_sync_pack_does_not_rewrite_an_equivalent_toml(tmp_path: Path):
    cook, mast, server = tmp_path / "cook", tmp_path / "master", tmp_path / "server"
    _pack(cook / "pk", _toml("P", {"SK_a": "Pack/SK_a"}), {"Pack/SK_a.uasset": b"a"})
    master.sync_pack("pk", cook, mast, server, deploy=False, restore=True, log=lambda m: None)
    reformatted = "# reformaté par le serveur\n" + (cook / "pk" / "Assets.toml").read_text(encoding="utf-8")
    (cook / "pk" / "Assets.toml").write_text(reformatted, encoding="utf-8")
    master.sync_pack("pk", cook, mast, server, deploy=False, restore=True, log=lambda m: None)
    assert (cook / "pk" / "Assets.toml").read_text(encoding="utf-8") == reformatted  # laissé tel quel
    assert not list((mast / "_history" / "pk").glob("cook-*.toml")) or len(list((mast / "_history" / "pk").glob("cook-*.toml"))) <= 1


def test_snapshot_changes_when_cook_writes(tmp_path: Path):
    _pack(tmp_path / "pk", _toml("P", {}), {"a.bin": b"a"})
    before = master.snapshot(tmp_path / "pk")
    (tmp_path / "pk" / "b.bin").write_bytes(b"b")
    assert master.snapshot(tmp_path / "pk") != before
