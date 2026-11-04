"""Génère Shared/VfxAssets.lua : la liste des systèmes de particules cuits, pack par pack, pour kimetsu-pandora.

    python unreal_tools/gen_vfx_assets.py

Lit l'Assets.toml de chaque pack (section [assets.particles]) dans le dossier Assets de chaque serveur, et écrit pour chacun sa propre
liste : un serveur ne propose que les effets qu'il possède. À relancer après chaque cuisson de VFX déployée sur un serveur.
"""
import argparse
import tomllib
from pathlib import Path

STEAM = Path(r"C:\Program Files (x86)\Steam\steamapps\common")
TARGETS = [
    (STEAM / "nanos-world-playtest" / "Server" / "Packages" / "kimetsu-pandora" / "Shared" / "VfxAssets.lua", STEAM / "nanos-world-playtest" / "Server" / "Assets"),
    (STEAM / "nanos-world-server" / "Packages" / "kimetsu-pandora" / "Shared" / "VfxAssets.lua", STEAM / "nanos-world-server" / "Assets"),
]


def particles_of(assets_dir: Path) -> dict[str, list[str]]:
    """{pack: [noms de systèmes de particules]} pour les packs de ce dossier qui en contiennent."""
    result = {}
    for toml_path in sorted(assets_dir.glob("*/Assets.toml")):
        doc = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        names = sorted(doc.get("assets", {}).get("particles", {}))
        if names:
            result[toml_path.parent.name] = names
    return result


def fx_meshes_of(assets_dir: Path) -> tuple[str, list[str], list[str]]:
    """(pack, formes SM_FX_*, matériaux M_FX_*/MI_FX_*) du pack cuit qui contient les meshes d'effet originaux
    (unreal_tools/import_fx_meshes.py, dossier Unreal BreathFx). Le pack est reconnu à ses formes SM_FX_*, quel que soit le nom que Forge lui a
    donné ; ("", [], []) s'il n'est pas cuit sur ce serveur."""
    for toml_path in sorted(assets_dir.glob("*/Assets.toml")):
        assets = tomllib.loads(toml_path.read_text(encoding="utf-8")).get("assets", {})
        meshes = sorted(name for name in assets.get("static_meshes", {}) if name.startswith("SM_FX_"))
        if meshes:
            materials = sorted(name for name in assets.get("materials", {}) if name.startswith(("M_FX_", "MI_FX_")))
            return toml_path.parent.name, meshes, materials
    return "", [], []


def build_fx(pack: str, meshes: list[str], materials: list[str]) -> str:
    def names(values):
        return "".join(f'\t\t"{name}",\n' for name in values)

    return (
        "-- Généré par unreal_tools/gen_vfx_assets.py à partir de l'Assets.toml du pack des meshes d'effet : ne pas modifier à la main.\n"
        "-- Le pack, ses formes (SM_FX_*) et ses matériaux (M_FX_*, MI_FX_*) réellement disponibles sur ce serveur ; vides tant qu'il n'est pas cuit.\n"
        f'return {{\n\tpack = "{pack}",\n\tmeshes = {{\n{names(meshes)}\t}},\n\tmaterials = {{\n{names(materials)}\t}},\n}}\n'
    )


def build(packs: dict[str, list[str]]) -> str:
    rows = "".join(f'\t["{pack}"] = {{\n' + "".join(f'\t\t"{name}",\n' for name in names) + "\t},\n" for pack, names in sorted(packs.items()))
    return (
        "-- Généré par unreal_tools/gen_vfx_assets.py à partir des Assets.toml des packs cuits : ne pas modifier à la main.\n"
        "-- { [pack] = { noms des systèmes de particules } } : les effets réellement disponibles sur ce serveur.\n"
        f"return {{\n{rows}}}\n"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--target", nargs=2, action="append", metavar=("LUA", "ASSETS"), help="fichier Lua à écrire et dossier Assets à lire (répétable)")
    args = ap.parse_args(argv)
    targets = [(Path(lua), Path(assets)) for lua, assets in args.target] if args.target else TARGETS
    for lua_path, assets_dir in targets:
        packs = particles_of(assets_dir) if assets_dir.exists() else {}
        lua_path.parent.mkdir(parents=True, exist_ok=True)
        lua_path.write_bytes(build(packs).encode("utf-8"))  # LF, comme le reste des packages
        count = sum(len(names) for names in packs.values())
        print(f"{lua_path} : {count} systèmes dans {len(packs)} packs ({', '.join(sorted(packs)) or 'aucun'})")
        fx_pack, meshes, materials = fx_meshes_of(assets_dir) if assets_dir.exists() else ("", [], [])
        fx_path = lua_path.with_name("FxMeshAssets.lua")
        fx_path.write_bytes(build_fx(fx_pack, meshes, materials).encode("utf-8"))
        print(f"{fx_path} : {len(meshes)} formes et {len(materials)} matériaux (pack {fx_pack or 'aucun'})")


if __name__ == "__main__":
    main()
