"""Génère Shared/Animations.lua (liste des animations des packs) pour le visualiseur d'animations de wakfu-rp.

    python unreal_tools/gen_anim_list.py

Lit [assets.animations] de l'Assets.toml de chaque pack (séquences A_*, montages AM_*) et écrit un fichier Lua dans chaque
copie du package wakfu-rp. Un pack qui n'est pas (encore) sur le serveur est ignoré, avec un message. À relancer après un
nouveau cook, une fois les packs envoyés au serveur par le watcher du master.
"""
import argparse
import tomllib
from pathlib import Path

STEAM = Path(r"C:\Program Files (x86)\Steam\steamapps\common")
PACKS = ["aksel-animations", "scythe"]
ASSETS = STEAM / "nanos-world-server" / "Assets"
OUTPUTS = [
    STEAM / "nanos-world-server" / "Packages" / "wakfu-rp" / "Shared" / "Animations.lua",
    STEAM / "nanos-world-playtest" / "Server" / "Packages" / "wakfu-rp" / "Shared" / "Animations.lua",
]


def split_names(names):
    """(séquences A_*, montages AM_*), triés. Les autres préfixes sont ignorés."""
    sequences = sorted(n for n in names if n.startswith("A_"))
    montages = sorted(n for n in names if n.startswith("AM_"))
    return sequences, montages


def _lua_list(field, names):
    items = "".join(f'\t\t\t\t"{n}",\n' for n in names)
    return f"\t\t\t{field} = {{\n{items}\t\t\t}},\n"


def build_lua(packs):
    """packs : liste de (nom du pack, noms d'animations)."""
    blocks = ""
    for pack, names in packs:
        sequences, montages = split_names(names)
        blocks += (
            "\t\t{\n"
            f'\t\t\tname = "{pack}",\n'
            f"{_lua_list('sequences', sequences)}"
            f"{_lua_list('montages', montages)}"
            "\t\t},\n"
        )
    return (
        "-- Généré par unreal_tools/gen_anim_list.py à partir de l'Assets.toml des packs : ne pas modifier à la main.\n"
        f"return {{\n\tpacks = {{\n{blocks}\t}},\n}}\n"
    )


def read_pack(assets, pack):
    """Noms d'animations d'un pack, ou None s'il n'a pas d'Assets.toml sous `assets`."""
    toml = assets / pack / "Assets.toml"
    if not toml.is_file():
        return None
    return tomllib.loads(toml.read_text(encoding="utf-8"))["assets"].get("animations", {})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pack", action="append", help=f"nom d'un pack d'assets (répétable ; défaut : {', '.join(PACKS)})")
    ap.add_argument("--assets", type=Path, default=ASSETS, help="dossier Assets qui contient les packs")
    ap.add_argument("--out", type=Path, action="append", help="fichier Lua à écrire (répétable ; défaut : les deux wakfu-rp)")
    args = ap.parse_args(argv)

    packs = []
    for pack in args.pack or PACKS:
        names = read_pack(args.assets, pack)
        if names is None:
            print(f"ignoré : {pack} (pas d'Assets.toml dans {args.assets / pack})")
            continue
        packs.append((pack, names))
        print(f"{pack} : {len(names)} animations")
    if not packs:
        raise SystemExit(f"aucun pack trouvé dans {args.assets}")

    text = build_lua(packs)
    for out in args.out or OUTPUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))  # LF, comme le reste du package
        print(f"écrit : {out}")


if __name__ == "__main__":
    main()
