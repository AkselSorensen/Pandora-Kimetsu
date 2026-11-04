"""Prépare le Katana Animation Pack (Unreal 4.27) pour nanos world dans le projet Unreal 5.7.

Unreal : Tools > Execute Python Script... puis choisir ce fichier (plugin "Python Editor Script Plugin" requis).
Commence avec LIMIT = 3 : le script traite trois animations et s'arrête, pour vérifier le résultat. Puis LIMIT = None.

Ce que fait le script, uniquement dans /Game/<PACK> (le reste du projet et le dossier source ne sont jamais touchés) :
  1. copie le pack dans Content/ (sans les groupes d'animations inutiles, la map et le sol de démo) ;
  2. met chaque animation sur SKEL_Mannequin, le squelette de nanos world ;
  3. crée un montage AM_* par animation ;
  4. LIMIT = None seulement : range le katana dans Meshes/ puis supprime la démo et les animations d'origine.

Noms : Forge utilise le nom de l'asset comme clé dans Assets.toml, donc ils doivent être uniques dans le pack.
Le pack contient des doublons (AS_Combo_Attack_All_Seq...) : le dossier d'origine est ajouté au nom en cas de collision.
"""
import os
import re
import shutil
import tempfile
import traceback

import unreal

SOURCE = r"C:\Users\azrae\Downloads\KatanaAnimationPack 4.27\KatanaAnimationPack 4.27\Content\Katana_Animations"
PACK = "Katana_Animations"  # dossier de Content = nom du pack nanos (Forge en fait un pack en kebab-case)
NANOS_SKELETON = "/Game/NanosWorld/Characters/Common/SKEL_Mannequin"
KEEP_GROUPS = ("02_Attack", "06_Dodge", "07_Roll", "08_Hit")  # dossiers de Animations/Sequence à garder
KEEP_MESHES = ("M_Katana", "Katana_sword", "Katana_sheath")  # katana et fourreau, à sauver de la démo
LIMIT = None  # 3 = essai sur trois animations seulement, sans nettoyage
CREATE_MONTAGES = True

ROOT = "/Game/" + PACK
SEQ_DIR = ROOT + "/Animations/Sequence"
NANOS_DIR = ROOT + "/Nanos"
MONTAGE_DIR = ROOT + "/Montages"
MESH_DIR = ROOT + "/Meshes"

eal = unreal.EditorAssetLibrary
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()


# --- noms et filtres (sans Unreal, testés dans tests/test_katana_script.py) -------------------------------------

def keep_source(rel):
    """Vrai si le fichier (chemin relatif au dossier source, avec /) doit être copié dans le projet."""
    parts = rel.split("/")
    if parts[:2] == ["Animations", "Sequence"] and len(parts) > 3:
        return parts[2] in KEEP_GROUPS
    if parts[:2] == ["Demo", "Maps"]:
        return False
    if parts[:2] == ["Demo", "Material"] and parts[-1].startswith("M_Floor"):
        return False
    return not parts[-1].startswith(".")


def seq_base(name):
    """AS_Combo_Attack_01_Seq -> Combo_Attack_01"""
    return re.sub(r"_Seq$", "", re.sub(r"^AS_", "", name))


def folder_tag(folder):
    """02_Attack/01_Combo_Attack_01 -> Combo_Attack_01 (dernier dossier, sans son numéro)."""
    return re.sub(r"^\d+_", "", folder.rstrip("/").split("/")[-1])


def unique_names(entries):
    """entries : [(dossier, nom_asset)] -> {(dossier, nom_asset): nom de base unique dans le pack}."""
    used, result = set(), {}
    for folder, name in sorted(entries):
        base = seq_base(name)
        if base in used:
            base = f"{base}_{folder_tag(folder)}"
        candidate, n = base, 2
        while candidate in used:
            candidate, n = f"{base}_{n}", n + 1
        used.add(candidate)
        result[(folder, name)] = candidate
    return result


def pack_slug(folder):
    """Katana_Animations -> katana-animations ; YufuPmVaasContent -> yufu-pm-vaas-content"""
    words = []
    for part in re.split(r"[_\W]+", folder):
        words += re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", part)
    return "-".join(w.lower() for w in words)


# --- étapes ------------------------------------------------------------------------------------------------------

def log(message):
    unreal.log("[katana] " + message)


def registry():
    return unreal.AssetRegistryHelpers.get_asset_registry()


def copy_pack():
    dest = os.path.join(unreal.Paths.project_content_dir(), PACK)
    copied = 0
    for dirpath, _, files in os.walk(SOURCE):
        rel_dir = os.path.relpath(dirpath, SOURCE).replace("\\", "/")
        for name in files:
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            target = os.path.join(dest, *rel.split("/"))
            if not keep_source(rel) or os.path.exists(target):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(os.path.join(dirpath, name), target)
            copied += 1
    registry().scan_paths_synchronous([ROOT], True)
    log(f"{copied} fichier(s) copiés dans {dest}")


def list_animations():
    """[(dossier relatif, nom de l'asset, chemin du package)] des AnimSequence d'origine."""
    found = []
    for data in registry().get_assets_by_path(SEQ_DIR, recursive=True):
        if str(data.asset_class_path.asset_name) != "AnimSequence":
            continue
        package = str(data.package_name)
        folder, _, name = package[len(SEQ_DIR) + 1:].rpartition("/")
        found.append((folder, name, package))
    return sorted(found)


def on_nanos_skeleton(asset, skeleton):
    return asset is not None and asset.get_editor_property("skeleton") == skeleton


def retarget(package, new_name, skeleton, tmp_dir):
    """Crée /Nanos/<new_name> sur SKEL_Mannequin à partir de l'animation d'origine. Vrai si réussi."""
    new_path = f"{NANOS_DIR}/{new_name}"
    anim = eal.load_asset(package)
    if anim is None:
        return False

    # 1) Assignation directe du squelette. Unreal 5.7 déclare la propriété en lecture seule : en général refusé.
    try:
        anim.set_editor_property("skeleton", skeleton)
        if on_nanos_skeleton(anim, skeleton) and eal.rename_asset(package, new_path):
            eal.save_asset(new_path)
            return True
    except Exception:
        pass

    # 2) Aller-retour FBX : export de l'animation, puis import sur SKEL_Mannequin sous son nouveau nom.
    fbx = os.path.join(tmp_dir, new_name + ".fbx")
    export = unreal.AssetExportTask()
    export.object = anim
    export.filename = fbx
    export.automated = True
    export.prompt = False
    export.replace_identical = True
    unreal.Exporter.run_asset_export_task(export)
    if not os.path.exists(fbx):
        log(f"  export FBX impossible : {package}")
        return False

    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", False)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("import_animations", True)
    options.set_editor_property("skeleton", skeleton)
    options.set_editor_property("original_import_type", unreal.FBXImportType.FBXIT_ANIMATION)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = NANOS_DIR
    task.destination_name = new_name
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    try:
        asset_tools.import_asset_tasks([task])
    except RuntimeError as exc:
        # Unreal remonte ses avertissements d'import en exception alors que l'asset est créé : ici, les pistes des os
        # Katana_weapon_01 / Katana_sheath_01 n'existent pas sur SKEL_Mannequin et sont ignorées (le katana sera un Melee).
        log(f"  avertissement d'import ignoré : {str(exc)[:160]}")
    if not eal.does_asset_exist(new_path):
        log(f"  import FBX impossible : {new_name}")
        return False
    return on_nanos_skeleton(eal.load_asset(new_path), skeleton)


def make_montage(seq_path, name, skeleton):
    path = f"{MONTAGE_DIR}/{name}"
    if eal.does_asset_exist(path):
        return True
    factory = unreal.AnimMontageFactory()
    factory.set_editor_property("target_skeleton", skeleton)
    factory.set_editor_property("source_animation", eal.load_asset(seq_path))
    montage = asset_tools.create_asset(name, MONTAGE_DIR, unreal.AnimMontage, factory)
    if montage is None:
        return False
    eal.save_asset(path)
    return True


def convert(base, package, skeleton, tmp_dir):
    """Une animation : A_<base> sur SKEL_Mannequin, puis AM_<base>. Renvoie les montages créés ; lève en cas d'échec."""
    seq_path = f"{NANOS_DIR}/A_{base}"
    if not on_nanos_skeleton(eal.load_asset(seq_path), skeleton):
        if not retarget(package, f"A_{base}", skeleton, tmp_dir):
            raise RuntimeError("changement de squelette impossible")
    montages = []
    if CREATE_MONTAGES:
        if not make_montage(seq_path, f"AM_{base}", skeleton):
            raise RuntimeError("création du montage impossible")
        montages.append(f"AM_{base}")
    log(f"  OK : {base}")
    return montages


def cleanup():
    """Katana et fourreau dans Meshes/, puis suppression de la démo et des animations d'origine."""
    eal.make_directory(MESH_DIR)
    for data in registry().get_assets_by_path(ROOT + "/Demo", recursive=True):
        if str(data.asset_name) in KEEP_MESHES:
            eal.rename_asset(str(data.package_name), f"{MESH_DIR}/{data.asset_name}")
    for folder in ("/Demo", "/Animations"):
        eal.delete_directory(ROOT + folder)
    log("démo et animations d'origine supprimées")


def main():
    if eal.does_directory_exist(NANOS_DIR) and not eal.does_directory_exist(SEQ_DIR):
        log("le pack est déjà terminé (plus d'animations d'origine) : rien à faire")
        return
    skeleton = eal.load_asset(NANOS_SKELETON)
    if skeleton is None:
        raise RuntimeError(f"SKEL_Mannequin introuvable : {NANOS_SKELETON}")

    copy_pack()
    animations = list_animations()
    names = unique_names([(folder, name) for folder, name, _ in animations])
    todo = animations[:LIMIT] if LIMIT else animations
    log(f"{len(animations)} animation(s) dans le pack, {len(todo)} traitée(s)")

    tmp_dir = tempfile.mkdtemp(prefix="katana_fbx_")
    failures, montages = [], []
    try:
        for folder, name, package in todo:
            try:
                montages += convert(names[(folder, name)], package, skeleton, tmp_dir)
            except Exception:  # une animation en échec ne doit pas arrêter les autres, et l'erreur doit rester lisible
                failures.append(package)
                log(f"  ÉCHEC : {package}\n{traceback.format_exc()}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if failures:
        log(f"{len(failures)} échec(s) : voir le journal ci-dessus. Pas de nettoyage. "
            "Si le squelette ne peut pas être changé, fais-le à la main (Property Matrix) puis relance.")
        return
    if LIMIT:
        log(f"Essai réussi sur {len(todo)} animation(s). Vérifie /Game/{PACK}/Nanos et Montages, "
            "puis mets LIMIT = None et relance.")
        return
    cleanup()
    slug = pack_slug(PACK)
    log(f"Terminé. Cuis avec Forge : le pack devrait s'appeler '{slug}'. Exemple de réglage Lua :")
    log("animations = { " + ", ".join(f'"{slug}::{m}"' for m in montages[:3]) + " }")


# Dans l'éditeur le script se lance tout seul ; les tests remplacent `unreal` par un module factice marqué FAKE_FOR_TESTS.
if not getattr(unreal, "FAKE_FOR_TESTS", False):
    main()
