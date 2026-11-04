import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "unreal_tools" / "gen_vfx_assets.py"
spec = importlib.util.spec_from_file_location("gen_vfx_assets", SCRIPT)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def write_pack(assets: Path, name: str, particles: list[str]):
    (assets / name).mkdir(parents=True)
    rows = "".join(f'{p} = "X/{p}"\n' for p in particles)
    (assets / name / "Assets.toml").write_text(f"[assets.static_meshes]\nSM_a = \"X/A\"\n\n[assets.particles]\n{rows}", encoding="utf-8")


def test_only_packs_with_particles_are_listed_sorted(tmp_path: Path):
    write_pack(tmp_path, "free-magic", ["NS_B", "NS_A"])
    write_pack(tmp_path, "scythe", [])
    write_pack(tmp_path, "vefects", ["NS_Trail_Water"])
    assert gen.particles_of(tmp_path) == {"free-magic": ["NS_A", "NS_B"], "vefects": ["NS_Trail_Water"]}


def test_build_is_a_lua_table_with_lf_endings():
    text = gen.build({"vefects": ["NS_Trail_Fire", "NS_Trail_Water"]})
    assert 'return {\n\t["vefects"] = {\n\t\t"NS_Trail_Fire",\n\t\t"NS_Trail_Water",\n\t},\n}\n' in text
    assert "\r" not in text and text.startswith("-- Généré par")


def test_each_target_gets_only_its_own_server_packs(tmp_path: Path):
    playtest, dedicated = tmp_path / "playtest", tmp_path / "dedicated"
    write_pack(playtest, "vefects", ["NS_Trail_Water"])
    write_pack(dedicated, "scythe", [])
    out_a, out_b = tmp_path / "a" / "VfxAssets.lua", tmp_path / "b" / "VfxAssets.lua"
    gen.main(["--target", str(out_a), str(playtest), "--target", str(out_b), str(dedicated)])
    assert b"NS_Trail_Water" in out_a.read_bytes()
    assert out_b.read_bytes().endswith(b"return {\n}\n")


def write_fx_pack(assets: Path, meshes: list[str], materials: list[str], name: str = "breath-fx"):
    (assets / name).mkdir(parents=True)
    rows = "".join(f'{m} = "BreathFx/Meshes/{m}"\n' for m in meshes)
    mats = "".join(f'{m} = "BreathFx/Materials/{m}"\n' for m in materials)
    (assets / name / "Assets.toml").write_text(f"[assets.static_meshes]\n{rows}\n[assets.materials]\n{mats}", encoding="utf-8")


def test_fx_meshes_and_materials_are_listed_sorted_and_filtered(tmp_path: Path):
    write_fx_pack(tmp_path, ["SM_FX_Ring", "SM_FX_Burst", "SM_Autre"], ["MI_FX_Eau", "M_FX_Glow", "M_Autre"])
    assert gen.fx_meshes_of(tmp_path) == ("breath-fx", ["SM_FX_Burst", "SM_FX_Ring"], ["MI_FX_Eau", "M_FX_Glow"])
    assert gen.fx_meshes_of(tmp_path / "absent") == ("", [], [])


def test_the_fx_pack_is_found_whatever_forge_named_it(tmp_path: Path):
    write_pack(tmp_path, "free-magic", ["NS_A"])  # un pack sans formes SM_FX_* est ignoré
    write_fx_pack(tmp_path, ["SM_FX_Spiral"], ["M_FX_Glow"], name="breathfx")
    assert gen.fx_meshes_of(tmp_path) == ("breathfx", ["SM_FX_Spiral"], ["M_FX_Glow"])


def test_build_fx_is_a_lua_table_with_lf_endings():
    text = gen.build_fx("breath-fx", ["SM_FX_Ring"], ["MI_FX_Eau"])
    assert 'pack = "breath-fx",' in text and '\tmeshes = {\n\t\t"SM_FX_Ring",\n\t},' in text and '\tmaterials = {\n\t\t"MI_FX_Eau",\n\t},' in text
    assert "\r" not in text and text.startswith("-- Généré par")


def test_main_writes_the_fx_list_next_to_the_effect_list(tmp_path: Path):
    assets = tmp_path / "assets"
    write_fx_pack(assets, ["SM_FX_Ring"], ["M_FX_Glow"])
    out = tmp_path / "Shared" / "VfxAssets.lua"
    gen.main(["--target", str(out), str(assets)])
    assert b'"SM_FX_Ring"' in (tmp_path / "Shared" / "FxMeshAssets.lua").read_bytes()
    gen.main(["--target", str(out), str(tmp_path / "vide")])
    assert b'pack = "",\n\tmeshes = {\n\t},' in (tmp_path / "Shared" / "FxMeshAssets.lua").read_bytes()


def test_missing_assets_folder_gives_an_empty_list(tmp_path: Path):
    out = tmp_path / "VfxAssets.lua"
    gen.main(["--target", str(out), str(tmp_path / "absent")])
    assert out.read_bytes().endswith(b"return {\n}\n")
