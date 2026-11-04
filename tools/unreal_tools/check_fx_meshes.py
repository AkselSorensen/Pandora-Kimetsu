"""Vérifie /Game/BreathFx après import_fx_meshes.py et supprime les restes de l'import.

Unreal : champ Cmd, py "<chemin de ce fichier>" ; le résultat est dans le journal (filtre : fxcheck).

Pour chacune des 12 formes SM_FX_* : elle existe, son emplacement de matériau 0 est M_FX_Glow, et sa boîte englobante (taille et position, en
cm, repère Unreal) correspond à celle que gen_fx_meshes.py a dessinée : cela prouve que l'échelle (x100) et les axes de l'import glTF sont bons.
Pour M_FX_Glow : mode de mélange, éclairage, double face, nombre de noeuds et entrées branchées. Pour chaque MI_FX_* : le parent et la couleur.

Reste de l'import : Interchange crée un dossier SM_FX_<forme>/Materials/M_FX_Placeholder par forme, devenu inutile puisque la forme utilise
M_FX_Glow. Ce script supprime ces dossiers, seulement si la forme ne s'en sert plus (sinon il le dit et n'y touche pas).
"""
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\azrae\Desktop\nanosworld\unreal_tools"
sys.path.insert(0, HERE)
import gen_fx_meshes  # noqa: E402  (stdlib seulement : sert à connaître les boîtes attendues)

MESHES = "/Game/BreathFx/Meshes"
MATERIALS = "/Game/BreathFx/Materials"
COLORS = ["Eau", "Foudre", "Flamme", "Vent", "Pierre", "Brume", "Insecte", "Demon", "Blanc"]
TOLERANCE = 3.0  # cm

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
problems = []


def log(message):
    unreal.log("[fxcheck] " + message)


def problem(message):
    problems.append(message)
    unreal.log_error("[fxcheck] PROBLÈME " + message)


def expected_box(name):
    mesh = gen_fx_meshes.SHAPES[name]()
    lows = [min(p[k] for p in mesh.positions) for k in range(3)]
    highs = [max(p[k] for p in mesh.positions) for k in range(3)]
    return [(lo + hi) / 2 for lo, hi in zip(lows, highs)], [(hi - lo) / 2 for lo, hi in zip(lows, highs)]


def check_mesh(name):
    path = "%s/SM_FX_%s" % (MESHES, name)
    if not eal.does_asset_exist(path):
        problem("%s : absent (%s)" % (name, path))
        return None
    mesh = eal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        problem("%s : ce n'est pas un StaticMesh (%s)" % (name, type(mesh).__name__))
        return None
    material = mesh.get_material(0)
    material_path = material.get_path_name() if material else "aucun"
    if "M_FX_Glow" not in material_path:
        problem("%s : matériau 0 = %s (attendu M_FX_Glow)" % (name, material_path))
    bounds = mesh.get_bounds()
    origin = (bounds.origin.x, bounds.origin.y, bounds.origin.z)
    extent = (bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z)
    centre, half = expected_box(name)
    off = [abs(a - b) for a, b in zip(origin, centre)] + [abs(a - b) for a, b in zip(extent, half)]
    verdict = "taille et axes OK" if max(off) <= TOLERANCE else "ÉCART %.1f cm" % max(off)
    if max(off) > TOLERANCE:
        problem("%s : boîte (centre %s, demi-taille %s) différente de l'attendu (centre %s, demi-taille %s)" % (
            name, tuple(round(v, 1) for v in origin), tuple(round(v, 1) for v in extent),
            tuple(round(v, 1) for v in centre), tuple(round(v, 1) for v in half)))
    nanite = "?"
    try:
        nanite = "oui" if mesh.get_editor_property("nanite_settings").enabled else "non"
    except Exception:  # noqa: BLE001
        pass
    log("%-10s matériau 0 = %-22s demi-taille X %6.1f Y %6.1f Z %6.1f  nanite %s  -> %s" % (
        name, os.path.basename(material_path).split(".")[0], extent[0], extent[1], extent[2], nanite, verdict))
    return mesh


def check_glow():
    path = MATERIALS + "/M_FX_Glow"
    if not eal.does_asset_exist(path):
        problem("M_FX_Glow absent")
        return
    material = eal.load_asset(path)
    blend = material.get_editor_property("blend_mode")
    two_sided = material.get_editor_property("two_sided")
    model = material.get_editor_property("shading_model")
    count = mel.get_num_material_expressions(material)
    wired = {}
    for label, prop in (("émissif", unreal.MaterialProperty.MP_EMISSIVE_COLOR), ("opacité", unreal.MaterialProperty.MP_OPACITY)):
        try:
            wired[label] = mel.get_material_property_input_node(material, prop) is not None
        except Exception:  # noqa: BLE001
            wired[label] = None
    log("M_FX_Glow : mélange %s, éclairage %s, double face %s, %d noeuds, branché %s" % (blend.name, model.name, two_sided, count, wired))
    if "ADDITIVE" not in blend.name:
        problem("M_FX_Glow : le mélange n'est pas additif")
    if not two_sided:
        problem("M_FX_Glow : pas double face")
    if count < 15:
        problem("M_FX_Glow : %d noeuds seulement (17 attendus)" % count)
    if wired.get("émissif") is False or wired.get("opacité") is False:
        problem("M_FX_Glow : l'émissif ou l'opacité n'est pas branché")


def check_instances():
    for color in COLORS:
        path = "%s/MI_FX_%s" % (MATERIALS, color)
        if not eal.does_asset_exist(path):
            problem("MI_FX_%s absent" % color)
            continue
        instance = eal.load_asset(path)
        parent = instance.get_editor_property("parent")
        parent_name = parent.get_name() if parent else "aucun"
        try:
            value = mel.get_material_instance_vector_parameter_value(instance, "Color")
            rgb = "(%.2f, %.2f, %.2f)" % (value.r, value.g, value.b)
        except Exception:  # noqa: BLE001
            rgb = "?"
        log("MI_FX_%-8s parent %-10s couleur %s" % (color, parent_name, rgb))
        if parent_name != "M_FX_Glow":
            problem("MI_FX_%s : parent %s (attendu M_FX_Glow)" % (color, parent_name))


def clean_leftovers(meshes):
    removed = 0
    for name, mesh in meshes.items():
        folder = "%s/SM_FX_%s" % (MESHES, name)
        if not eal.does_directory_exist(folder):
            continue
        material = mesh.get_material(0) if mesh else None
        if material is None or "M_FX_Glow" not in material.get_path_name():
            log("%s : dossier d'import conservé (la forme n'utilise pas encore M_FX_Glow)" % folder)
            continue
        if eal.delete_directory(folder):
            removed += 1
    log("%d dossiers de restes d'import supprimés" % removed)


def attempt(label, function, *args):
    """Une vérification qui plante est notée comme un problème sans arrêter les suivantes."""
    try:
        return function(*args)
    except Exception as error:  # noqa: BLE001
        problem("%s : erreur du script (%s)" % (label, error))
        return None


attempt("M_FX_Glow", check_glow)
attempt("instances", check_instances)
found = {}
for shape in sorted(gen_fx_meshes.SHAPES):
    found[shape] = attempt(shape, check_mesh, shape)
attempt("nettoyage", clean_leftovers, {shape: mesh for shape, mesh in found.items() if mesh is not None})
count = sum(1 for mesh in found.values() if mesh is not None)
if problems:
    unreal.log_error("[fxcheck] %d formes sur 12, %d problème(s) : voir les lignes PROBLÈME ci-dessus" % (count, len(problems)))
else:
    log("TOUT EST BON : %d formes sur 12, matériaux et instances en place. Tu peux cuire /Game/BreathFx avec Forge." % count)
