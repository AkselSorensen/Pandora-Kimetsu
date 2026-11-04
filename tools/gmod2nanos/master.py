"""Master des Asset Packs cuisinés par Forge : cumule les cuissons au lieu de les écraser.

Forge copie la cuisson dans <serveur>/Assets/<pack> et réécrit Assets.toml avec seulement ce que le projet Unreal
contient à ce moment-là : les entrées (et le titre / l'auteur) des cuissons précédentes disparaissent. Le master ne
supprime jamais rien : il fusionne les fichiers et les Assets.toml, garde l'historique des Assets.toml remplacés,
puis redéploie le résultat sur le serveur dédié et dans le dossier de cuisson.

    python -m gmod2nanos.master sync maps yufu-pm-vaas-content --deploy maps
    python -m gmod2nanos.master watch --deploy maps
"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import os
import re
import shutil
import time
import tomllib
from datetime import datetime
from pathlib import Path

STEAM = Path(r"C:\Program Files (x86)\Steam\steamapps\common")
COOK_DIR = STEAM / "nanos-world-playtest" / "Server" / "Assets"  # là où Forge copie la cuisson
SERVER_DIR = STEAM / "nanos-world-server" / "Assets"  # serveur dédié (Lancer-Wakfu-RP.bat)
MASTER_DIR = Path.home() / "Documents" / "nanos-master"
TOML = "Assets.toml"
HISTORY_KEEP = 20
# Forge nomme le pack d'après le dossier Content d'Unreal ; on le publie sous un autre nom (dossier cuit -> nom publié).
ALIASES = {"yufu-pm-vaas-content": "pandora-demonslayer", "katana-animations": "aksel-animations"}


# --- Assets.toml -----------------------------------------------------------------------------------------------

def read_toml(path: Path) -> dict | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _union(a: list, b: list) -> list:
    return list(dict.fromkeys([*a, *b]))


def merge_toml(base: dict | None, new: dict) -> dict:
    """Méta du master conservée, entrées cumulées, la cuisson la plus récente l'emporte sur une même clé."""
    if not base:
        return new
    doc = {k: dict(v) for k, v in base.items()}
    doc.setdefault("meta", dict(new.get("meta", {})))
    for name, lists in (("asset_pack", "assets_requirements"), ("unreal", "unreal_folders")):
        old, cooked = doc.get(name, {}), new.get(name, {})
        doc[name] = {**old, **cooked, lists: _union(old.get(lists, []), cooked.get(lists, []))}
    assets = doc.setdefault("assets", {})
    for section, entries in new.get("assets", {}).items():
        assets[section] = {**assets.get(section, {}), **entries}
    for name, table in new.items():
        doc.setdefault(name, dict(table))
    return doc


_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+$")


def _key(key: str) -> str:
    return key if _BARE_KEY.match(key) else json.dumps(key, ensure_ascii=False)


def _value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_value(v) for v in value) + "]"
    raise TypeError(f"valeur TOML non gérée : {value!r}")


def _dump_table(name: str, table: dict, out: list[str]) -> None:
    out.append(f"[{name}]")
    out += [f"{_key(k)} = {_value(v)}" for k, v in table.items() if not isinstance(v, dict)]
    out.append("")
    for k, v in table.items():
        if isinstance(v, dict):
            _dump_table(f"{name}.{_key(k)}", v, out)


def dump_toml(doc: dict) -> str:
    """Même mise en forme que Forge : [meta], [asset_pack], [unreal], puis [assets.*]."""
    head = [k for k in ("meta", "asset_pack", "unreal") if k in doc]
    rest = [k for k in doc if k not in (*head, "assets")]
    out: list[str] = []
    for name in [*head, *rest, *(["assets"] if "assets" in doc else [])]:
        _dump_table(_key(name), doc[name], out)
    return "\n".join(out).rstrip("\n") + "\n"


def _same_content(path: Path, doc: dict) -> bool:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")) == doc
    except (OSError, tomllib.TOMLDecodeError):
        return False


def _toml_fingerprint(path: Path) -> str | None:
    """Empreinte du contenu (pas de la mise en forme) d'un Assets.toml, None s'il est absent ou illisible."""
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return hashlib.sha1(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()


def _write_toml(path: Path, doc: dict, history: Path, label: str, stamp: str) -> bool:
    """Écrit Assets.toml si son contenu change, après avoir copié l'ancien dans l'historique. True si écrit.

    Seul le contenu compte : le serveur nanos réécrit Assets.toml à sa façon (commentaires, indentation) à chaque
    chargement. Le réécrire à notre tour relançait le chargement du pack en pleine partie."""
    data = dump_toml(doc).encode("utf-8")
    if path.exists():
        if _same_content(path, doc):
            return False
        history.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, history / f"{label}-{stamp}.toml")
        for old in sorted(history.glob(f"{label}-*.toml"))[:-HISTORY_KEEP]:
            old.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return True


# --- fichiers --------------------------------------------------------------------------------------------------

def _needs_copy(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    s, d = src.stat(), dst.stat()
    if s.st_size != d.st_size:
        return True
    if abs(s.st_mtime - d.st_mtime) < 2:
        return False
    if filecmp.cmp(src, dst, shallow=False):
        os.utime(dst, ns=(s.st_atime_ns, s.st_mtime_ns))  # contenu identique : évite de recomparer au prochain passage
        return False
    return True


def merge_tree(src: Path, dst: Path) -> int:
    """Copie dans dst les fichiers de src nouveaux ou modifiés, sans jamais rien supprimer. Retourne le nombre copié."""
    copied = 0
    for dirpath, _, files in os.walk(src):
        rel = Path(dirpath).relative_to(src)
        for name in files:
            if name == TOML and rel == Path("."):
                continue
            s, d = Path(dirpath) / name, dst / rel / name
            if _needs_copy(s, d):
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
                copied += 1
    return copied


def list_packs(cook: Path, published: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """Packs écrits par Forge : on ignore les copies publiées sous un alias, que le master écrit lui-même."""
    return sorted(p.name for p in cook.iterdir() if p.is_dir() and p.name[0] not in "._" and p.name not in published)


def snapshot(pack_dir: Path) -> tuple[int, int, str | None]:
    """(nombre de fichiers, mtime le plus récent, empreinte d'Assets.toml) : change dès que Forge écrit du contenu.

    Assets.toml n'est comparé que par son contenu, pas par sa date : le serveur nanos le reformate à chaque chargement."""
    count = newest = 0
    for dirpath, _, files in os.walk(pack_dir):
        for name in files:
            if name == TOML and Path(dirpath) == pack_dir:
                continue
            try:
                mtime = os.stat(os.path.join(dirpath, name)).st_mtime_ns
            except OSError:  # Forge remplace ses fichiers pendant la copie : l'un a pu disparaître depuis le parcours
                continue
            count += 1
            newest = max(newest, mtime)
    return count, newest, _toml_fingerprint(pack_dir / TOML)


# --- synchronisation -------------------------------------------------------------------------------------------

def sync_pack(pack: str, cook: Path, master: Path, server: Path, deploy: bool, restore: bool, log=print,
              name: str | None = None) -> None:
    """`pack` : dossier écrit par Forge ; `name` : nom sous lequel il est publié (master, serveur, copie dans cook)."""
    name = name or pack
    cook_pack, master_pack, server_pack = cook / pack, master / name, server / name
    history = master / "_history" / name
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if not master_pack.is_dir() and server_pack.is_dir():
        # premier passage : on part de ce que le serveur a déjà, pour ne rien perdre de ses fichiers ni de son Assets.toml
        log(f"  {name}: master créé depuis le serveur ({merge_tree(server_pack, master_pack)} fichiers)")
    base = read_toml(master_pack / TOML) or read_toml(server_pack / TOML)
    copied = merge_tree(cook_pack, master_pack)
    cooked = read_toml(cook_pack / TOML)
    doc = merge_toml(base, cooked) if cooked else base
    if doc is not None and _write_toml(master_pack / TOML, doc, history, "master", stamp):
        log(f"  {name}: Assets.toml du master mis à jour")
    log(f"  {name}: {copied} fichier(s) de la cuisson ajoutés au master")

    targets = [("serveur", server_pack)] * deploy + [("cook", cook / name)] * restore
    for label, target in targets:
        n = merge_tree(master_pack, target)
        wrote = doc is not None and _write_toml(target / TOML, doc, history, label, stamp)
        log(f"  {name}: {label} <- master ({n} fichier(s){', Assets.toml' if wrote else ''})")


def watch(cook: Path, master: Path, server: Path, deploy: set[str], restore: bool,
          interval: float, settle: float, aliases: dict[str, str] | None = None, log=print) -> None:
    """Surveille le dossier de cuisson ; une fois un pack stable depuis `settle` secondes, le fusionne dans le master."""
    aliases = aliases or {}
    published = set(aliases.values())
    seen = {p: snapshot(cook / p) for p in list_packs(cook, published)}
    pending: dict[str, tuple[tuple[int, int, str | None], float]] = {}
    log(f"Surveillance de {cook} ({len(seen)} packs). Ctrl+C pour arrêter.")
    while True:
        time.sleep(interval)
        for pack in list_packs(cook, published):
            snap = snapshot(cook / pack)
            if snap == seen.get(pack):
                pending.pop(pack, None)
                continue
            if pending.get(pack, (None, 0))[0] != snap:
                pending[pack] = (snap, time.monotonic())  # encore en train d'écrire
                continue
            if time.monotonic() - pending[pack][1] < settle:
                continue
            del pending[pack]
            name = aliases.get(pack, pack)
            log(f"[{datetime.now():%H:%M:%S}] cuisson détectée : {pack}" + (f" (publié sous {name})" if name != pack else ""))
            try:
                sync_pack(pack, cook, master, server, name in deploy or (server / name).is_dir(), restore, log, name)
            except Exception as exc:  # une erreur sur un pack ne doit pas arrêter la surveillance
                log(f"  {name}: ERREUR {exc!r}")
            seen[pack] = snapshot(cook / pack)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m gmod2nanos.master", description=__doc__.split("\n\n")[0])
    ap.add_argument("action", choices=["sync", "watch"], help="sync : une fois ; watch : à chaque cuisson Forge")
    ap.add_argument("packs", nargs="*", help="packs à traiter pour sync (défaut : tous ceux du dossier de cuisson)")
    ap.add_argument("--cook", type=Path, default=COOK_DIR, help="dossier Assets où Forge copie la cuisson")
    ap.add_argument("--master", type=Path, default=MASTER_DIR, help="dossier du master")
    ap.add_argument("--server", type=Path, default=SERVER_DIR, help="dossier Assets du serveur dédié")
    ap.add_argument("--deploy", action="append", default=[], metavar="PACK",
                    help="pack à envoyer au serveur même s'il n'y est pas encore (ceux qui y sont déjà le sont toujours)")
    ap.add_argument("--alias", action="append", default=[], metavar="CUIT=PUBLIÉ",
                    help="publier le pack cuit CUIT sous le nom PUBLIÉ (s'ajoute à ALIASES)")
    ap.add_argument("--no-restore", action="store_true", help="ne pas réécrire le master dans le dossier de cuisson")
    ap.add_argument("--interval", type=float, default=3, help="secondes entre deux relevés (watch)")
    ap.add_argument("--settle", type=float, default=10, help="secondes sans changement avant de traiter un pack (watch)")
    args = ap.parse_args(argv)

    deploy, restore = set(args.deploy), not args.no_restore
    aliases = {**ALIASES, **dict(a.split("=", 1) for a in args.alias)}
    if args.action == "watch":
        try:
            watch(args.cook, args.master, args.server, deploy, restore, args.interval, args.settle, aliases)
        except KeyboardInterrupt:
            print("Arrêt.")
        return
    for pack in args.packs or list_packs(args.cook, set(aliases.values())):
        name = aliases.get(pack, pack)
        sync_pack(pack, args.cook, args.master, args.server, name in deploy or (args.server / name).is_dir(),
                  restore, name=name)


if __name__ == "__main__":
    main()
