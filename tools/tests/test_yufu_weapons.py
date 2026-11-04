import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "unreal_tools" / "gen_yufu_weapons.py"
spec = importlib.util.spec_from_file_location("gen_yufu_weapons", SCRIPT)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

WEAPONS = [
    {"asset": "pk::SM_claymore10", "source": "models/izuki/claymore10.mdl"},
    {"asset": "pk::SM_claymore2", "source": "models/izuki/claymore2.mdl"},
    {"asset": "pk::SM_katana1", "source": "models/izuki/katana1.mdl"},
    {"asset": "pk::SM_aquila", "source": "models/aquila.mdl"},
    {"asset": "pk::SM_lance5", "source": "models/izuki/lance5.mdl"},
    {"asset": "pk::SM_pas_cuite", "source": "models/pas_cuite.mdl"},
]


def test_group_of_families_and_misc():
    assert gen.group_of("models/izuki/katana12.mdl") == "Katana"
    assert gen.group_of("models/izuki/spear3.mdl") == "Spear"
    assert gen.group_of("models/aquila.mdl") == "Divers"
    assert gen.group_of("models\\izuki\\lance5.mdl") == "Lance"


def test_build_keeps_only_cooked_weapons_sorted_naturally_by_group():
    cooked = {"SM_claymore10", "SM_claymore2", "SM_katana1", "SM_aquila", "SM_lance5"}
    text, entries = gen.build(WEAPONS, cooked, "pk")
    assert entries == [
        ("katana1", "Katana"),
        ("claymore2", "Claymore"),
        ("claymore10", "Claymore"),
        ("lance5", "Lance"),
        ("aquila", "Divers"),
    ]
    assert text.startswith("-- Généré par") and 'pack = "pk",' in text
    assert '{ "claymore2", "Claymore" },' in text and "pas_cuite" not in text


def write_gltf(models: Path, name: str, top: float):
    (models / f"SM_{name}").mkdir(parents=True)
    doc = {"meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}], "accessors": [{"min": [-0.1, -0.15, -0.1], "max": [0.1, top, 0.1]}]}
    (models / f"SM_{name}" / f"SM_{name}.gltf").write_text(json.dumps(doc), encoding="utf-8")


def test_tip_is_the_top_of_the_blade_axis_in_centimetres(tmp_path: Path):
    write_gltf(tmp_path, "katana1", 1.183)
    assert gen.tip_of(tmp_path, "katana1") == 118
    assert gen.tip_of(tmp_path, "absent") is None


def test_build_writes_the_tip_only_when_known():
    text, entries = gen.build(WEAPONS, {"SM_katana1", "SM_aquila"}, "pk", {"katana1": 118})
    assert '{ "katana1", "Katana", 118 },' in text and '{ "aquila", "Divers" },' in text
    assert entries == [("katana1", "Katana"), ("aquila", "Divers")]


def test_main_reads_the_tips_from_the_gltf_folder(tmp_path: Path):
    (tmp_path / "pk").mkdir()
    (tmp_path / "pk" / "Assets.toml").write_text('[assets.static_meshes]\nSM_katana1 = "X/K"\n', encoding="utf-8")
    weapons = tmp_path / "weapons.json"
    weapons.write_text(json.dumps(WEAPONS), encoding="utf-8")
    write_gltf(tmp_path / "models", "katana1", 1.183)
    out = tmp_path / "YufuWeapons.lua"
    gen.main(["--pack", "pk", "--weapons", str(weapons), "--assets", str(tmp_path), "--models", str(tmp_path / "models"), "--out", str(out)])
    assert b'{ "katana1", "Katana", 118 },' in out.read_bytes()


def test_main_writes_every_output(tmp_path: Path):
    (tmp_path / "pk").mkdir()
    (tmp_path / "pk" / "Assets.toml").write_text('[assets.static_meshes]\nSM_katana1 = "X/K"\nSM_aquila = "X/A"\n', encoding="utf-8")
    weapons = tmp_path / "weapons.json"
    weapons.write_text(json.dumps(WEAPONS), encoding="utf-8")
    a, b = tmp_path / "a" / "YufuWeapons.lua", tmp_path / "b" / "YufuWeapons.lua"
    gen.main(["--pack", "pk", "--weapons", str(weapons), "--assets", str(tmp_path), "--out", str(a), "--out", str(b)])
    assert a.read_bytes() == b.read_bytes()
    assert b"\r\n" not in a.read_bytes() and b'"katana1"' in a.read_bytes()


def test_main_fails_when_nothing_is_cooked(tmp_path: Path):
    (tmp_path / "pk").mkdir()
    (tmp_path / "pk" / "Assets.toml").write_text("[assets.static_meshes]\n", encoding="utf-8")
    weapons = tmp_path / "weapons.json"
    weapons.write_text(json.dumps(WEAPONS), encoding="utf-8")
    with pytest.raises(SystemExit):
        gen.main(["--pack", "pk", "--weapons", str(weapons), "--assets", str(tmp_path), "--out", str(tmp_path / "x.lua")])
    assert not (tmp_path / "x.lua").exists()
