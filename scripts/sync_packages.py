"""Copie les packages entre le dépôt (packages/) et un serveur nanos world.

    python scripts/sync_packages.py install --server "C:/chemin/vers/nanos-world-server"   # dépôt -> serveur
    python scripts/sync_packages.py pull    --server "C:/chemin/vers/nanos-world-server"   # serveur -> dépôt
    ajouter --dry-run pour voir ce qui serait copié sans rien écrire

Le dossier du serveur est celui qui contient NanosWorldServer.exe et Packages/. Les deux sens ignorent ce qui ne doit jamais être versionné
(vidéos, assets cuits, images héritées de l'ancien projet) et, à l'installation, gardent les listes d'effets générées par serveur
(Shared/VfxAssets.lua et Shared/FxMeshAssets.lua) quand elles existent déjà : elles décrivent les packs réellement cuits sur ce serveur,
voir docs/ASSETS.md pour les régénérer.
"""
import argparse
import filecmp
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGES = REPO / "packages"
SKIP_PARTS = {"__pycache__", ".git", "node_modules", "Saved", "logs"}
SKIP_SUFFIXES = {".pyc", ".uasset", ".uexp", ".ubulk", ".umap", ".webm", ".mp4", ".log"}
SKIP_PATHS = ("wakfu-rp/Client/UI/img/reroll", "wakfu-rp/Client/UI/img/logo.png")
GENERATED = ("wakfu-rp/Shared/VfxAssets.lua", "wakfu-rp/Shared/FxMeshAssets.lua")


def wanted(relative: str, path: Path) -> bool:
    if any(part in SKIP_PARTS for part in path.parts) or path.suffix.lower() in SKIP_SUFFIXES:
        return False
    return not any(relative == skip or relative.startswith(skip + "/") for skip in SKIP_PATHS)


def copy_packages(source: Path, target: Path, names: list[str], keep_generated: bool, dry_run: bool) -> None:
    created = updated = same = skipped = 0
    for name in names:
        for path in sorted((source / name).rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(source).as_posix()
            if not wanted(relative, path.relative_to(source)):
                continue
            destination = target / relative
            if keep_generated and relative in GENERATED and destination.exists():
                skipped += 1
                continue
            if destination.exists() and filecmp.cmp(path, destination, shallow=False):
                same += 1
                continue
            created, updated = (created + 1, updated) if not destination.exists() else (created, updated + 1)
            print(("[a copier] " if dry_run else "copié     ") + relative)
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
    print(f"{created} créés, {updated} mis à jour, {same} identiques, {skipped} gardés (listes générées du serveur)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("direction", choices=["install", "pull"], help="install : dépôt -> serveur ; pull : serveur -> dépôt")
    parser.add_argument("--server", required=True, type=Path, help="dossier du serveur nanos world (celui qui contient Packages/)")
    parser.add_argument("--dry-run", action="store_true", help="n'écrit rien, liste seulement")
    parser.add_argument("--force", action="store_true", help="écrase aussi les listes d'effets générées du serveur")
    args = parser.parse_args()

    server_packages = args.server / "Packages"
    if not server_packages.is_dir():
        raise SystemExit(f"{server_packages} n'existe pas : --server doit pointer sur le dossier qui contient NanosWorldServer.exe")
    names = sorted(p.name for p in PACKAGES.iterdir() if p.is_dir())
    if args.direction == "install":
        copy_packages(PACKAGES, server_packages, names, keep_generated=not args.force, dry_run=args.dry_run)
    else:
        present = [name for name in names if (server_packages / name).is_dir()]
        copy_packages(server_packages, PACKAGES, present, keep_generated=False, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
