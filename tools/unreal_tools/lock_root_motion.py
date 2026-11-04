"""Règle le déplacement des animations d'un dossier : sur place, ou déplacement conservé (root motion).

Unreal : Tools > Execute Python Script... puis choisir ce fichier, ou dans le champ Cmd : py "<chemin du fichier>".

Symptôme corrigé : pendant l'animation le personnage glisse (l'os racine se déplace), puis revient d'un coup à son point
de départ. Deux réglages sur chaque AnimSequence :
  - sur place  : « Enable Root Motion » faux, « Force Root Lock » vrai. Le corps bouge en entier, la racine reste en place ;
  - déplacement : « Enable Root Motion » vrai, « Force Root Lock » faux. Le déplacement est pris par le personnage (sa capsule),
    qui reste donc là où l'animation le laisse. Ça ne marche que si nanos world joue le root motion : à vérifier en jeu.

MOVING liste les mots qui, dans le nom d'une animation, la rangent en « déplacement » ; les autres restent sur place.
Il faut ensuite recuire le pack avec Forge.

Limite : le verrouillage ne retire que le déplacement de la racine ; s'il vient d'un autre os (le bassin), il reste visible.
"""
import traceback

import unreal

FOLDERS = ["/Game/Katana_Animations/Nanos", "/Game/Scythe/Nanos"]  # dossiers traités (ceux qui n'existent pas sont ignorés)
MOVING = ("Dodge", "Roll", "Dash", "Run_Attack", "Speed")  # animations dont le déplacement doit être conservé ; () = tout sur place

eal = unreal.EditorAssetLibrary


def log(message):
    unreal.log("[racine] " + message)


def moves(name):
    """Vrai si le nom d'animation contient un des mots de MOVING."""
    return any(word in name for word in MOVING)


def apply(folder):
    """Règle chaque AnimSequence du dossier. Renvoie (sur place, déplacement, échecs)."""
    in_place = moving = failed = 0
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    for data in registry.get_assets_by_path(folder, recursive=True):
        if str(data.asset_class_path.asset_name) != "AnimSequence":
            continue
        path = str(data.package_name)
        move = moves(str(data.asset_name))
        try:
            anim = eal.load_asset(path)
            anim.set_editor_property("enable_root_motion", move)
            anim.set_editor_property("force_root_lock", not move)
            eal.save_asset(path)
            moving, in_place = moving + move, in_place + (not move)
        except Exception:
            failed += 1
            log(f"  ÉCHEC : {path}\n{traceback.format_exc()}")
    return in_place, moving, failed


def main():
    totals = [0, 0, 0]
    for folder in FOLDERS:
        if not eal.does_directory_exist(folder):
            log(f"{folder} : absent, ignoré")
            continue
        counts = apply(folder)
        totals = [a + b for a, b in zip(totals, counts)]
        log(f"{folder} : {counts[0]} sur place, {counts[1]} avec déplacement, {counts[2]} échec(s)")
    log(f"Terminé : {totals[0]} sur place, {totals[1]} avec déplacement. "
        "Recuis maintenant le pack avec Forge (Plateformes, Préparer le contenu, Windows).")
    if totals[2]:
        log(f"{totals[2]} échec(s) : voir le journal ci-dessus.")


# Dans l'éditeur le script se lance tout seul ; les tests remplacent `unreal` par un module factice marqué FAKE_FOR_TESTS.
if not getattr(unreal, "FAKE_FOR_TESTS", False):
    main()
