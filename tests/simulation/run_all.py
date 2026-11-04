"""Lance les tests de simulation du mode de jeu, sans lancer nanos world : le Lua du serveur et du client tourne dans un faux moteur (lupa).

    pip install lupa
    python tests/simulation/run_all.py          # logique, serveur et client
    python tests/simulation/run_all.py --ui     # en plus : rendu du HUD dans Microsoft Edge (captures dans tests/simulation/out/)

Chaque script affiche ce qu'il vérifie et sort en erreur au premier ECHEC.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    ("données, serveur et client du démon", "demon_check.py", []),
    ("serveur : arrivée, techniques, forge, traînée, voies", "ds_check.py", []),
    ("client : menu de traînée et touches", "trail_menu_check.py", []),
    ("effets Niagara : plans, repli, client", "vfx_check.py", []),
    ("formes lumineuses : plans et lecture", "fx_mesh_check.py", []),
]
UI = ("HUD dans Edge : DOM et captures", "ui_demon_preview.py", ["test"])


def main() -> int:
    scripts = SCRIPTS + ([UI] if "--ui" in sys.argv else [])
    failed = []
    for label, name, args in scripts:
        result = subprocess.run([sys.executable, str(HERE / name), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        problems = [line.strip() for line in result.stdout.splitlines() if "ECHEC" in line]
        status = "OK    " if result.returncode == 0 and not problems else "ECHEC "
        print(f"{status}{label}  ({name})")
        if status.startswith("ECHEC"):
            failed.append(name)
            for line in (problems or result.stderr.splitlines()[-3:])[:5]:
                print("      " + line)
    print()
    print("tout passe" if not failed else f"{len(failed)} test(s) en échec : {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
