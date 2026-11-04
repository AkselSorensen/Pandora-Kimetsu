"""Génère Shared/YufuWeapons.lua (armes du pack yufu-arme-test) pour kimetsu-pandora et pour le menu de props.

    python unreal_tools/gen_yufu_weapons.py

Croise `weapons.json` (écrit par gmod2nanos : les armes du pack et leur dossier d'origine) avec l'Assets.toml du pack cuit sur
le serveur : seules les armes réellement cuites sont listées. À relancer après un nouveau cook du pack.
"""
import argparse
import json
import re
import tomllib
from pathlib import Path

STEAM = Path(r"C:\Program Files (x86)\Steam\steamapps\common")
PACK = "yufu-arme-test"
WEAPONS = Path.home() / "Downloads" / "yufu-arme-test-nanos-grip" / "weapons.json"
MODELS = Path.home() / "Downloads" / "yufu-arme-test-nanos-grip" / "1-unreal" / "YufuArmeTest" / "Models"
ASSETS = STEAM / "nanos-world-server" / "Assets"
OUTPUTS = [
    STEAM / "nanos-world-server" / "Packages" / "kimetsu-pandora" / "Shared" / "YufuWeapons.lua",
    STEAM / "nanos-world-playtest" / "Server" / "Packages" / "kimetsu-pandora" / "Shared" / "YufuWeapons.lua",
    STEAM / "nanos-world-playtest" / "Server" / "Packages" / "gmod-props-menu" / "Shared" / "YufuWeapons.lua",
]

FAMILIES = {"katana": "Katana", "claymore": "Claymore", "lance": "Lance"}  # armes du dossier models/izuki/
GROUP_ORDER = ["Katana", "Claymore", "Lance", "Divers"]


def group_of(source: str) -> str:
    """Catégorie dans le menu : la famille des armes du dossier izuki (katana1, katana2... -> Katana), sinon Divers."""
    if "/izuki/" in source.lower().replace("\\", "/"):
        family = re.sub(r"\d+$", "", Path(source).stem)
        return FAMILIES.get(family, family.capitalize())
    return "Divers"


def natural(text: str):
    """Tri « humain » : claymore2 avant claymore10."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


def tip_of(models: Path, name: str) -> int | None:
    """Distance (cm) du centre de la poignée à la pointe de la lame, ou None si le glTF manque.

    Les glTF de la conversion sont déjà orientés pour la main : la lame suit leur axe Y (l'axe haut d'Unreal après import), donc la
    pointe est au sommet de Y, en mètres, que l'import d'Unreal multiplie par 100.
    """
    path = models / f"SM_{name}" / f"SM_{name}.gltf"
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    position = doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    return round(doc["accessors"][position]["max"][1] * 100)


def build(weapons: list[dict], cooked: set[str], pack: str, tips: dict[str, int] | None = None) -> tuple[str, list[tuple[str, str]]]:
    """(texte Lua, [(nom sans SM_, catégorie)]) des armes cuites, triées par catégorie puis par nom.

    tips : {nom sans SM_: distance poignée-pointe en cm}, écrite en troisième valeur de chaque ligne quand elle est connue.
    """
    tips = tips or {}
    entries = []
    for weapon in weapons:
        key = weapon["asset"].split("::", 1)[1]
        if key in cooked and key.startswith("SM_"):
            entries.append((key[3:], group_of(weapon["source"])))

    def order(entry):
        name, group = entry
        rank = GROUP_ORDER.index(group) if group in GROUP_ORDER else len(GROUP_ORDER)
        return rank, group, natural(name)

    entries.sort(key=order)
    rows = "".join(
        f'\t\t{{ "{name}", "{group}", {tips[name]} }},\n' if name in tips else f'\t\t{{ "{name}", "{group}" }},\n' for name, group in entries
    )
    text = (
        "-- Généré par unreal_tools/gen_yufu_weapons.py à partir de weapons.json et de l'Assets.toml du pack : ne pas modifier à la main.\n"
        "-- weapons = { nom du mesh sans le préfixe SM_, catégorie dans le menu de props, distance poignée-pointe de la lame en cm (si connue) }\n"
        f'return {{\n\tpack = "{pack}",\n\tweapons = {{\n{rows}\t}},\n}}\n'
    )
    return text, entries


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pack", default=PACK, help="nom du pack d'assets")
    ap.add_argument("--weapons", type=Path, default=WEAPONS, help="weapons.json de la conversion")
    ap.add_argument("--assets", type=Path, default=ASSETS, help="dossier Assets qui contient le pack cuit")
    ap.add_argument("--models", type=Path, default=MODELS, help="dossier des glTF de la conversion (SM_<nom>/SM_<nom>.gltf), pour la pointe des lames")
    ap.add_argument("--out", type=Path, action="append", help="fichier Lua à écrire (répétable ; défaut : kimetsu-pandora x2 et menu de props)")
    args = ap.parse_args(argv)

    weapons = json.loads(args.weapons.read_text(encoding="utf-8"))
    doc = tomllib.loads((args.assets / args.pack / "Assets.toml").read_text(encoding="utf-8"))
    cooked = set(doc["assets"].get("static_meshes", {}))
    tips = {}
    for weapon in weapons:
        name = weapon["asset"].split("::", 1)[1][3:]
        tip = tip_of(args.models, name)
        if tip:
            tips[name] = tip
    text, entries = build(weapons, cooked, args.pack, tips)
    if not entries:
        raise SystemExit("aucune arme cuite trouvée : vérifie weapons.json et l'Assets.toml du pack")
    print(f"{len(entries)} armes cuites sur {len(weapons)} converties")
    for out in args.out or OUTPUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))  # LF, comme le reste des packages
        print(f"écrit : {out}")


if __name__ == "__main__":
    main()
