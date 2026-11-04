"""Prépare les VFX Niagara du projet pour la cuisson Forge : uniquement les effets, aucun modèle d'arme.

Unreal : champ Cmd, py "<chemin de ce fichier>" ; le résultat est dans le journal (filtre : vfx).

1. D'abord, avant toute analyse : ajoute les dossiers de COOK à « Autres répertoires de ressources à préparer » (cuits par Forge) et ceux de
   NEVER à « Répertoires à ne jamais préparer » : les démos de ces packs contiennent des épées et des mannequins que la cuisson ne doit
   pas embarquer. Cette partie ne dépend de rien d'autre et s'enregistre dans DefaultGame.ini.
2. Ensuite, par précaution : liste les systèmes Niagara de COOK, vérifie que chacun se charge, suit leurs dépendances et signale
   « [vfx] ARME » tout modèle d'arme tiré dans la cuisson et « [vfx] MANQUANT » tout asset absent (un système qui dépend d'un asset
   absent ne se charge pas). Une erreur ici n'empêche jamais l'étape 1.

Seuls les dossiers de VFX sont cuits : leurs matériaux, textures et meshes d'effet (plans, spirales, croissants) suivent comme
dépendances, sans les démos ni les cartes (des centaines de Mo dans Free_Magic et Free_Spells). À relancer après chaque ajout de pack
de VFX (ajouter son dossier à COOK et sa démo à NEVER).
"""
import re

import unreal

COOK = [
    "/Game/Vefects/Essential_Trails/Shared/Particles",
    "/Game/Free_Magic/VFX_Niagara",
    "/Game/Free_Spells/VFX_Niagara",
    "/Game/SwordTrailVFX/VFX",
]

# Démos des packs de VFX : épées, mannequins, animations, cartes. Jamais cuites.
NEVER = [
    "/Game/SwordTrailVFX/Demo",
    "/Game/Free_Magic/Demo",
    "/Game/Free_Spells/Demo",
]

# Nom d'asset (pas de dossier) qui désigne une arme ; un mesh ou une animation de ce genre ne doit pas être cuit avec les effets.
WEAPON = re.compile(r"sword|katana|blade|knife|dagger|staff|wand|weapon|axe|spear|bow|gun|rifle|mace|hammer|shield", re.I)
MODEL_CLASSES = ("StaticMesh", "SkeletalMesh", "AnimSequence", "AnimMontage", "Blueprint", "PhysicsAsset", "Skeleton")


def log(message):
    unreal.log("[vfx] " + message)


def set_cook_lists_on_disk():
    """Unreal 5.7 n'expose pas ProjectPackagingSettings en Python : on écrit les lignes dans DefaultGame.ini (copie .avant-vfx à côté)."""
    import os

    path = os.path.join(str(unreal.Paths.project_config_dir()), "DefaultGame.ini")
    raw = open(path, "rb").read()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    lines = raw.decode("utf-8").split(newline)
    wanted = ['+DirectoriesToAlwaysCook=(Path="%s")' % p for p in COOK] + ['+DirectoriesToNeverCook=(Path="%s")' % p for p in NEVER]
    new = [line for line in wanted if line not in lines]
    if new:
        open(path + ".avant-vfx", "wb").write(raw)
        anchor = max([i for i, line in enumerate(lines) if line.startswith("+DirectoriesToAlwaysCook=")] or [len(lines) - 1])
        lines[anchor + 1:anchor + 1] = new
        open(path, "wb").write(newline.join(lines).encode("utf-8"))
    log("DefaultGame.ini : %d lignes ajoutées (déjà présentes : %d). Si Forge ne voit pas les dossiers, ferme et rouvre Unreal." % (len(new), len(wanted) - len(new)))


def set_cook_lists():
    """Étape 1 : listes de cuisson du projet (en mémoire pour Forge, puis sur le disque)."""
    if not hasattr(unreal, "ProjectPackagingSettings"):
        return set_cook_lists_on_disk()
    settings = unreal.get_default_object(unreal.ProjectPackagingSettings)
    cook = [str(d.path) for d in settings.get_editor_property("directories_to_always_cook")]
    never = [str(d.path) for d in settings.get_editor_property("directories_to_never_cook")]
    wanted_cook = cook + [p for p in COOK if p not in cook]
    wanted_never = never + [p for p in NEVER if p not in never]
    if wanted_cook != cook:
        settings.set_editor_property("directories_to_always_cook", [unreal.DirectoryPath(path=p) for p in wanted_cook])
    if wanted_never != never:
        settings.set_editor_property("directories_to_never_cook", [unreal.DirectoryPath(path=p) for p in wanted_never])
    if wanted_cook != cook or wanted_never != never:
        try:
            settings.save_config()
        except Exception as error:  # noqa: BLE001
            log("listes modifiées en mémoire (Forge les verra), mais pas enregistrées dans DefaultGame.ini (%s)" % error)
    log("cuits toujours : %s" % [str(d.path) for d in settings.get_editor_property("directories_to_always_cook")])
    log("jamais cuits : %s" % [str(d.path) for d in settings.get_editor_property("directories_to_never_cook")])
    missing = [p for p in COOK if p not in [str(d.path) for d in settings.get_editor_property("directories_to_always_cook")]]
    log("liste de cuisson : %s" % ("OK, les 4 dossiers de VFX y sont" if not missing else "INCOMPLÈTE, manque %s" % missing))


def class_name(data):
    try:
        return str(data.asset_class_path.asset_name)
    except Exception:  # noqa: BLE001
        return str(data.get_editor_property("asset_class"))


def dependency_options():
    try:
        return unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True)
    except Exception:  # noqa: BLE001
        options = unreal.AssetRegistryDependencyOptions()
        options.set_editor_property("include_hard_package_references", True)
        options.set_editor_property("include_soft_package_references", False)
        return options


def analyse():
    """Étape 2 : chargement des systèmes, dépendances manquantes et armes."""
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous(COOK, True)
    options = dependency_options()

    total = bad = 0
    used_by = {}  # dépendance /Game/... -> systèmes qui l'utilisent
    for folder in COOK:
        systems = [d for d in registry.get_assets_by_path(folder, recursive=True) if class_name(d) == "NiagaraSystem"]
        loaded = 0
        for data in systems:
            try:
                ok = data.get_asset() is not None
            except Exception as error:  # noqa: BLE001
                ok = False
                log("ERREUR %s : %s" % (data.asset_name, error))
            loaded += 1 if ok else 0
            if not ok:
                bad += 1
                log("illisible : %s" % data.package_name)
            try:
                for dependency in registry.get_dependencies(data.package_name, options) or []:
                    if str(dependency).startswith("/Game/"):
                        used_by.setdefault(str(dependency), set()).add(str(data.asset_name))
            except Exception as error:  # noqa: BLE001
                log("dépendances illisibles pour %s : %s" % (data.asset_name, error))
        total += len(systems)
        log("%s : %d systèmes Niagara, %d chargés" % (folder, len(systems), loaded))

    missing = weapons = 0
    for package in sorted(used_by):
        name = package.rsplit("/", 1)[-1]
        try:
            object_path = "%s.%s" % (package, name)
            try:
                data = registry.get_asset_by_object_path(unreal.SoftObjectPath(object_path))
            except Exception:  # noqa: BLE001
                data = registry.get_asset_by_object_path(object_path)
            exists = data is not None and data.is_valid()
        except Exception:  # noqa: BLE001
            data, exists = None, True  # impossible à vérifier : on ne crie pas au manquant
        if not exists:
            missing += 1
            log("MANQUANT : %s (utilisé par %d systèmes, par exemple %s)" % (package, len(used_by[package]), sorted(used_by[package])[0]))
        elif data is not None and class_name(data) in MODEL_CLASSES and WEAPON.search(name):
            weapons += 1
            log("ARME : %s (%s, utilisé par %s) : à retirer de ces effets avant la cuisson" % (package, class_name(data), sorted(used_by[package])))
    log("analyse : %d systèmes, %d illisibles, %d assets suivis, %d manquants, %d armes" % (total, bad, len(used_by), missing, weapons))


try:
    set_cook_lists()
except Exception as error:  # noqa: BLE001
    log("ÉCHEC des listes de cuisson (%s) : ajoute à la main, dans Paramètres du projet > Empaquetage > « Autres répertoires de ressources à préparer » : %s" % (error, COOK))

try:
    analyse()
except Exception as error:  # noqa: BLE001
    log("analyse interrompue (%s) : sans conséquence sur la liste de cuisson ci-dessus" % error)

log("terminé")
