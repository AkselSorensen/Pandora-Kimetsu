"""Prépare le Scythe Animation Pack (mannequin UE5) pour nanos world dans le projet Unreal 5.7.

Unreal : Tools > Execute Python Script... puis choisir ce fichier, ou dans le champ Cmd : py "<chemin du fichier>".
Commence avec LIMIT = 3 : le script traite trois animations et s'arrête, pour vérifier le résultat. Puis LIMIT = None.

Les animations du pack sont faites pour le mannequin UE5 (Manny), alors que nanos utilise le mannequin UE4 (SKEL_Mannequin) :
il faut les retargeter. Le pack fournit déjà le retargeter RTG_UE5Manny_UE4Manny (IK Retargeter, UE5 Manny -> UE4 Manny).

Ce que fait le script, uniquement dans /Game/<PACK> (le reste du projet et le dossier source ne sont jamais touchés) :
  1. copie le pack dans Content/ (sans les variantes à déplacement intégré, les groupes inutiles, la map et Quinn) ;
  2. retarget en lot vers le mannequin de nanos avec le retargeter du pack ; si Unreal ne sait pas produire directement un
     résultat sur SKEL_Mannequin, retarget vers le UE4 Manny du pack puis export/import FBX sur SKEL_Mannequin ;
  3. range chaque animation sous /Nanos avec un nom unique A_Scythe_*, racine verrouillée pour qu'elle reste sur place ;
  4. LIMIT = None seulement : range la faux dans Meshes/, puis supprime la démo et les animations d'origine.

Noms : Forge utilise le nom de l'asset comme clé dans Assets.toml, donc ils doivent être uniques dans le pack.
"""
import os
import re
import shutil
import tempfile
import traceback

import unreal

SOURCE = r"C:\Users\azrae\Downloads\Scythe_Animation_Pack___40_5.0_____5.8__41_\Scythe Animation Pack (5.0 – 5.8)\Content\Scythe"
PACK = "Scythe"  # dossier de Content = nom du pack nanos (Forge en fait un pack en kebab-case : scythe)
NANOS_SKELETON = "/Game/NanosWorld/Characters/Common/SKEL_Mannequin"
NANOS_MESH = "/Game/NanosWorld/Characters/Mannequin/SK_Mannequin"  # mesh de nanos sur SKEL_Mannequin
KEEP_GROUPS = ("02_Attack", "06_Dodge", "07_Roll", "08_Hit")  # dossiers de Animation/Sequence à garder
SKIP_FOLDERS = ("01_RM",)  # variantes avec déplacement intégré (root motion) : nanos ne les gère pas, on garde les « IP »
KEEP_MESHES = ("Scythe", "M_Asset")  # la faux et son matériau, à sauver de la démo
LIMIT = None  # 3 = essai sur trois animations seulement, sans nettoyage
LOCK_ROOT = True  # verrouille l'os racine : l'animation reste sur place (sinon le personnage glisse puis revient au départ)
NAME_PREFIX = "A_Scythe_"  # préfixe des animations finales : évite les collisions si le pack rejoint un autre pack

ROOT = "/Game/" + PACK
SEQ_DIR = ROOT + "/Animation/Sequence"
NANOS_DIR = ROOT + "/Nanos"
MESH_DIR = ROOT + "/Meshes"
UE5_SOURCE_MESH = ROOT + "/Demo/Characters/Mannequins/Meshes/SKM_Manny"
UE4_PACK_MESH = ROOT + "/Demo/Characters/Mannequin_UE4/Meshes/SK_Mannequin"
RETARGETER = ROOT + "/Demo/Characters/Mannequin_UE4/Rigs/RTG_UE5Manny_UE4Manny"
RT_PREFIX = "RT_"  # préfixe temporaire des copies retargetées, créées à côté des originaux

eal = unreal.EditorAssetLibrary
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()


# --- noms et filtres (sans Unreal, testés dans tests/test_scythe_script.py) ---------------------------------------

def keep_source(rel):
    """Vrai si le fichier (chemin relatif au dossier source, avec /) doit être copié dans le projet."""
    parts = rel.split("/")
    if parts[:2] == ["Animation", "Sequence"] and len(parts) > 3:
        return parts[2] in KEEP_GROUPS and not any(p in SKIP_FOLDERS for p in parts[3:-1])
    if parts[:2] == ["Demo", "Maps"]:
        return False
    if parts[:2] == ["Demo", "Material"] and parts[-1].startswith("M_Floor"):
        return False
    if "Quinn" in parts[-1] or "Quinn" in parts[:-1]:
        return False
    return not parts[-1].startswith(".")


def seq_base(name):
    """AS_Combo_Attack_01_01_Seq -> Combo_Attack_01_01"""
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
    """Scythe -> scythe ; YufuPmVaasContent -> yufu-pm-vaas-content"""
    words = []
    for part in re.split(r"[_\W]+", folder):
        words += re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", part)
    return "-".join(w.lower() for w in words)


# --- étapes ------------------------------------------------------------------------------------------------------

def log(message):
    unreal.log("[scythe] " + message)


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


def asset_class(data):
    return str(data.asset_class_path.asset_name)


def list_animations():
    """[(dossier relatif, nom, AssetData)] des AnimSequence d'origine (hors copies RT_ temporaires)."""
    found = []
    for data in registry().get_assets_by_path(SEQ_DIR, recursive=True):
        name = str(data.asset_name)
        if asset_class(data) != "AnimSequence" or name.startswith(RT_PREFIX):
            continue
        folder = str(data.package_name)[len(SEQ_DIR) + 1:].rpartition("/")[0]
        found.append((folder, name, data))
    return sorted(found, key=lambda e: (e[0], e[1]))


def on_nanos_skeleton(asset, skeleton):
    return asset is not None and asset.get_editor_property("skeleton") == skeleton


def drop_leftovers():
    """Copies RT_AS_* temporaires (créées à la racine de /Game par le retarget) : on les supprime avant et après."""
    for path, recursive in (("/Game", False), (ROOT, True)):
        for data in registry().get_assets_by_path(path, recursive=recursive):
            if str(data.asset_name).startswith(RT_PREFIX + "AS_"):
                eal.delete_asset(str(data.package_name))


def fbx_roundtrip(package, new_name, skeleton, tmp_dir):
    """Exporte l'animation en FBX puis l'importe sur SKEL_Mannequin sous /Nanos/<new_name>. Vrai si réussi."""
    new_path = f"{NANOS_DIR}/{new_name}"
    anim = eal.load_asset(package)
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
        # Unreal remonte ses avertissements d'import en exception alors que l'asset est créé (os absents du squelette).
        log(f"  avertissement d'import ignoré : {str(exc)[:160]}")
    return eal.does_asset_exist(new_path) and on_nanos_skeleton(eal.load_asset(new_path), skeleton)


def lock_root(path):
    """Verrouille la racine de l'animation : elle reste sur place au lieu de déplacer le personnage puis de le ramener."""
    if not LOCK_ROOT:
        return
    anim = eal.load_asset(path)
    anim.set_editor_property("enable_root_motion", False)
    anim.set_editor_property("force_root_lock", True)
    eal.save_asset(path)


def retarget_batch(pending):
    """Retargete les animations d'un coup avec le retargeter du pack. Renvoie les AssetData créés (copies RT_)."""
    source = eal.load_asset(UE5_SOURCE_MESH)
    retargeter = eal.load_asset(RETARGETER)
    if source is None or retargeter is None:
        raise RuntimeError(f"mesh source ou retargeter introuvable : {UE5_SOURCE_MESH} / {RETARGETER}")
    for mesh_path in (NANOS_MESH, UE4_PACK_MESH):
        target = eal.load_asset(mesh_path)
        if target is None:
            log(f"  mesh cible introuvable : {mesh_path}")
            continue
        created = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [entry[2] for entry in pending], source, target, retargeter, "", "", RT_PREFIX, "", False, False)
        if created:
            log(f"retarget vers {mesh_path} : {len(created)} animation(s) créées")
            return list(created)
        log(f"retarget vers {mesh_path} : aucune animation produite")
    return []


def rounds_of(pending):
    """Lots où chaque nom d'animation n'apparaît qu'une fois : le retarget range ses copies à la racine de /Game, où un
    nom en double serait renommé et ne se laisserait plus rattacher à son original."""
    rounds = []
    for entry in pending:
        for batch in rounds:
            if all(other[1] != entry[1] for other in batch):
                batch.append(entry)
                break
        else:
            rounds.append([entry])
    return rounds


def convert(pending, names, skeleton, tmp_dir):
    """Retargete puis range les animations. Renvoie la liste des échecs (chemins d'origine)."""
    failures = []
    for batch in rounds_of(pending):
        by_name = {name: (folder, name) for folder, name, _ in batch}
        seen = set()
        created = retarget_batch(batch)
        for data in created:
            package = str(data.package_name)
            rt_name = str(data.asset_name)
            orig = rt_name[len(RT_PREFIX):]
            key = by_name.get(orig) if rt_name.startswith(RT_PREFIX) else None
            if key is None:
                log(f"  copie inconnue : {package}")
                continue
            seen.add(orig)
            final_name = NAME_PREFIX + names[key]
            final_path = f"{NANOS_DIR}/{final_name}"
            try:
                if on_nanos_skeleton(eal.load_asset(package), skeleton):
                    ok = eal.rename_asset(package, final_path)
                    if ok:
                        eal.save_asset(final_path)
                else:
                    ok = fbx_roundtrip(package, final_name, skeleton, tmp_dir)
                if not ok:
                    raise RuntimeError("rangement ou changement de squelette impossible")
                lock_root(final_path)
                log(f"  OK : {final_name}")
            except Exception:
                failures.append(package)
                log(f"  ÉCHEC : {package}\n{traceback.format_exc()}")
        for data in created:  # copies restées à la racine (export FBX, échecs) : on libère leurs noms pour le lot suivant
            if eal.does_asset_exist(str(data.package_name)):
                eal.delete_asset(str(data.package_name))
        for orig, (folder, name) in by_name.items():
            if orig not in seen:
                failures.append(f"{SEQ_DIR}/{folder}/{name}")
                log(f"  pas de copie retargetée pour {SEQ_DIR}/{folder}/{name}")
    return failures


def cleanup():
    """La faux dans Meshes/, puis suppression de la démo et des animations d'origine."""
    eal.make_directory(MESH_DIR)
    for data in registry().get_assets_by_path(ROOT + "/Demo", recursive=True):
        if str(data.asset_name) in KEEP_MESHES:
            eal.rename_asset(str(data.package_name), f"{MESH_DIR}/{data.asset_name}")
    for folder in ("/Demo", "/Animation"):
        eal.delete_directory(ROOT + folder)
    drop_leftovers()
    log("démo, animations d'origine et copies temporaires supprimées")


def main():
    if eal.does_directory_exist(NANOS_DIR) and not eal.does_directory_exist(SEQ_DIR):
        log("le pack est déjà terminé (plus d'animations d'origine) : rien à faire")
        return
    skeleton = eal.load_asset(NANOS_SKELETON)
    if skeleton is None:
        raise RuntimeError(f"SKEL_Mannequin introuvable : {NANOS_SKELETON}")

    copy_pack()
    drop_leftovers()
    animations = list_animations()
    names = unique_names([(folder, name) for folder, name, _ in animations])
    todo = animations[:LIMIT] if LIMIT else animations
    pending = [entry for entry in todo
               if not on_nanos_skeleton(eal.load_asset(f"{NANOS_DIR}/{NAME_PREFIX}{names[(entry[0], entry[1])]}"), skeleton)]
    log(f"{len(animations)} animation(s) dans le pack, {len(todo)} traitée(s), {len(pending)} à retargeter")

    tmp_dir = tempfile.mkdtemp(prefix="scythe_fbx_")
    failures = []
    try:
        if pending:
            failures = convert(pending, names, skeleton, tmp_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if failures:
        log(f"{len(failures)} échec(s) : voir le journal ci-dessus. Pas de nettoyage.")
        return
    if LIMIT:
        log(f"Essai réussi sur {len(todo)} animation(s). Vérifie /Game/{PACK}/Nanos, puis mets LIMIT = None et relance.")
        return
    cleanup()
    slug = pack_slug(PACK)
    final = sorted(str(d.asset_name) for d in registry().get_assets_by_path(NANOS_DIR, recursive=True))
    log(f"Terminé : {len(final)} animations. Ajoute /Game/{PACK} aux dossiers à cuire, puis cuis avec Forge : "
        f"le pack devrait s'appeler '{slug}'. Exemple :")
    log("animations = { " + ", ".join(f'"{slug}::{n}"' for n in final[:3]) + " }")


# Dans l'éditeur le script se lance tout seul ; les tests remplacent `unreal` par un module factice marqué FAKE_FOR_TESTS.
if not getattr(unreal, "FAKE_FOR_TESTS", False):
    main()
