"""Importe les meshes d'effet originaux (fx_meshes/*.gltf, voir gen_fx_meshes.py) dans /Game/BreathFx et crée leurs matériaux.

Unreal : champ Cmd, py "<chemin de ce fichier>" ; le résultat est dans le journal (filtre : fx).

Crée :
  /Game/BreathFx/Materials/M_FX_Glow        matériau lumineux (additif, sans éclairage, double face) dont les bords et les pointes s'estompent
                                            d'après les UV ; paramètres Color, Intensity, Fade (1 = visible, 0 = invisible), FadeU, FadeV
  /Game/BreathFx/Materials/MI_FX_<voie>     une instance par voie de wakfu-rp (couleur) et MI_FX_Blanc
  /Game/BreathFx/Meshes/SM_FX_<forme>       les 12 formes, leur emplacement de matériau 0 sur M_FX_Glow, sans collision

Le dossier /Game/BreathFx doit ensuite être cuit (DefaultGame.ini : +DirectoriesToAlwaysCook=(Path="/Game/BreathFx")). Un pas qui échoue
est journalisé sans arrêter les suivants.
"""
import os

import unreal

FOLDER = "BreathFx"
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # exécuté sans __file__
    HERE = r"C:\Users\azrae\Desktop\nanosworld\unreal_tools"
SOURCE = os.path.normpath(os.path.join(HERE, "..", "fx_meshes"))

MESHES = "/Game/%s/Meshes" % FOLDER
MATERIALS = "/Game/%s/Materials" % FOLDER

# Une instance par voie de wakfu-rp (couleur linéaire r, g, b) ; Blanc sert aux essais.
COLORS = {
    "Eau": (0.10, 0.45, 1.00),
    "Foudre": (1.00, 0.85, 0.10),
    "Flamme": (1.00, 0.30, 0.05),
    "Vent": (0.30, 1.00, 0.60),
    "Pierre": (0.75, 0.55, 0.30),
    "Brume": (0.70, 0.85, 1.00),
    "Insecte": (0.65, 0.30, 1.00),
    "Demon": (1.00, 0.05, 0.12),
    "Blanc": (1.00, 1.00, 1.00),
}

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def log(message):
    unreal.log("[fx] " + message)


def step(name, function):
    """Exécute un pas ; une erreur est journalisée et le script continue."""
    try:
        return function()
    except Exception as error:  # noqa: BLE001
        unreal.log_error("[fx] ÉCHEC %s : %s" % (name, error))
        return None


def node(material, kind, x, y):
    return mel.create_material_expression(material, kind, x, y)


def build_glow():
    """Matériau M_FX_Glow : émissif = Color × Intensity, opacité = estompage en u et en v × Fade."""
    path = MATERIALS + "/M_FX_Glow"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    material = asset_tools.create_asset("M_FX_Glow", MATERIALS, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property("two_sided", True)

    uv = node(material, unreal.MaterialExpressionTextureCoordinate, -1600, 0)

    def channel(red, name, y):
        mask = node(material, unreal.MaterialExpressionComponentMask, -1400, y)
        mask.set_editor_property("r", red)
        mask.set_editor_property("g", not red)
        mask.set_editor_property("b", False)
        mask.set_editor_property("a", False)
        mel.connect_material_expressions(uv, "", mask, "")
        return mask

    def parameter(kind, name, value, y):
        p = node(material, kind, -1400, y)
        p.set_editor_property("parameter_name", name)
        p.set_editor_property("default_value", value)
        return p

    def edge(component, fade_name, fade_default, y):
        """sin(pi * x) ^ Fade : 0 aux bords, 1 au milieu."""
        sine = node(material, unreal.MaterialExpressionSine, -1150, y)
        sine.set_editor_property("period", 2.0)  # sin(2 * pi * x / 2) = sin(pi * x)
        mel.connect_material_expressions(component, "", sine, "")
        power = node(material, unreal.MaterialExpressionPower, -950, y)
        mel.connect_material_expressions(sine, "", power, "Base")
        mel.connect_material_expressions(parameter(unreal.MaterialExpressionScalarParameter, fade_name, fade_default, y + 120), "", power, "Exponent")
        return power

    along = edge(channel(True, "u", -150), "FadeU", 0.6, -150)
    across = edge(channel(False, "v", 150), "FadeV", 1.2, 150)

    mask = node(material, unreal.MaterialExpressionMultiply, -700, 0)
    mel.connect_material_expressions(along, "", mask, "A")
    mel.connect_material_expressions(across, "", mask, "B")
    opacity = node(material, unreal.MaterialExpressionMultiply, -500, 0)
    mel.connect_material_expressions(mask, "", opacity, "A")
    mel.connect_material_expressions(parameter(unreal.MaterialExpressionScalarParameter, "Fade", 1.0, 300), "", opacity, "B")
    saturate = node(material, unreal.MaterialExpressionSaturate, -320, 0)
    mel.connect_material_expressions(opacity, "", saturate, "")

    color = parameter(unreal.MaterialExpressionVectorParameter, "Color", unreal.LinearColor(1.0, 1.0, 1.0, 1.0), -400)
    intensity = parameter(unreal.MaterialExpressionScalarParameter, "Intensity", 6.0, -300)
    tinted = node(material, unreal.MaterialExpressionMultiply, -1150, -400)
    mel.connect_material_expressions(color, "", tinted, "A")
    mel.connect_material_expressions(intensity, "", tinted, "B")
    glow = node(material, unreal.MaterialExpressionMultiply, -320, -300)
    mel.connect_material_expressions(tinted, "", glow, "A")
    mel.connect_material_expressions(saturate, "", glow, "B")

    mel.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(saturate, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(material)
    eal.save_loaded_asset(material)
    log("matériau M_FX_Glow créé")
    return material


def build_instances(parent):
    done = 0
    for name, (r, g, b) in COLORS.items():
        path = "%s/MI_FX_%s" % (MATERIALS, name)
        if eal.does_asset_exist(path):
            eal.delete_asset(path)
        instance = asset_tools.create_asset("MI_FX_" + name, MATERIALS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(instance, parent)
        mel.set_material_instance_vector_parameter_value(instance, "Color", unreal.LinearColor(r, g, b, 1.0))
        eal.save_loaded_asset(instance)
        done += 1
    log("%d instances de matériau créées" % done)


def import_meshes(glow):
    files = sorted(f for f in os.listdir(SOURCE) if f.lower().endswith(".gltf")) if os.path.isdir(SOURCE) else []
    if not files:
        unreal.log_error("[fx] aucun .gltf dans %s : lance d'abord python unreal_tools/gen_fx_meshes.py" % SOURCE)
        return
    tasks = []
    for name in files:
        task = unreal.AssetImportTask()
        task.filename = os.path.join(SOURCE, name)
        task.destination_path = MESHES
        task.automated = True
        task.replace_existing = True
        task.save = True
        tasks.append(task)
    asset_tools.import_asset_tasks(tasks)

    ok = 0
    for name, task in zip(files, tasks):
        stem = os.path.splitext(name)[0]
        expected = "%s/%s" % (MESHES, stem)
        if not eal.does_asset_exist(expected):  # Interchange peut nommer le mesh autrement : on le renomme
            for obj_path in list(task.imported_object_paths or []):
                asset = eal.load_asset(obj_path)
                if isinstance(asset, unreal.StaticMesh):
                    eal.rename_asset(asset.get_path_name(), expected)
                    break
        mesh = eal.load_asset(expected) if eal.does_asset_exist(expected) else None
        if mesh is None:
            unreal.log_error("[fx] ÉCHEC import de %s" % name)
            continue
        step("matériau de " + stem, lambda: mesh.set_material(0, glow))
        step("nanite de " + stem, lambda: mesh.set_editor_property("nanite_settings", _without_nanite(mesh)))
        step("collision de " + stem, lambda: unreal.EditorStaticMeshLibrary.remove_collisions(mesh))
        eal.save_loaded_asset(mesh)
        leftover = "%s/%s" % (MESHES, stem)  # Interchange y a laissé un matériau M_FX_Placeholder devenu inutile
        if eal.does_directory_exist(leftover):
            step("restes d'import de " + stem, lambda: eal.delete_directory(leftover))
        ok += 1
    log("%d meshes importés sur %d" % (ok, len(files)))


def _without_nanite(mesh):
    settings = mesh.get_editor_property("nanite_settings")
    settings.enabled = False
    return settings


glow_material = step("matériau lumineux", build_glow)
if glow_material is not None:
    step("instances de matériau", lambda: build_instances(glow_material))
else:
    glow_material = eal.load_asset(MATERIALS + "/M_FX_Glow") if eal.does_asset_exist(MATERIALS + "/M_FX_Glow") else None
step("meshes", lambda: import_meshes(glow_material))
log("terminé : vérifie /Game/%s dans le Content Browser, puis cuis le dossier avec Forge" % FOLDER)
