"""Mesure le repère de meshes d'armes dans Unreal : axe de la lame, garde, largeur, épaisseur, courbure. Lecture seule.

Unreal : champ Cmd, py "<chemin de ce fichier>" ; le résultat est dans le journal (filtre : mesure).

Sert à savoir comment nanos world tient une arme : le Katana_sword du pack aksel-animations est bien tenu sans réglage,
son repère est donc la référence. Les mêmes mesures sur un sabre converti disent s'il est dans le même repère.
"""
import math

import unreal

ASSETS = [
    "/Game/Katana_Animations/Meshes/Katana_sword",  # référence : bien tenu en jeu
    "/Game/YufuArmeTest/Models/SM_katana1/SM_katana1",
    "/Game/YufuArmeTest/Models/SM_mitsurisword/SM_mitsurisword",
]
BINS = 14


def log(message):
    unreal.log("[mesure] " + message)


def vertices(mesh):
    """Tous les sommets du LOD 0, en pur Python."""
    points = []
    for section in range(mesh.get_num_sections(0)):
        data = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, section)
        points += [(v.x, v.y, v.z) for v in data[0]]
    return points


def span(values):
    return max(values) - min(values)


def measure(path):
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if mesh is None:
        return log("%s : introuvable" % path)
    box = mesh.get_bounding_box()
    log("=== %s" % path)
    log("boîte : min (%.1f, %.1f, %.1f) max (%.1f, %.1f, %.1f)" % (box.min.x, box.min.y, box.min.z, box.max.x, box.max.y, box.max.z))
    try:
        for socket in mesh.get_editor_property("sockets"):
            log("socket %s : %s" % (socket.get_editor_property("socket_name"), socket.get_editor_property("relative_location")))
    except Exception:
        pass
    points = vertices(mesh)
    if not points:
        return log("pas de sommets lisibles")
    axes = list("XYZ")
    extent = [span([p[i] for p in points]) for i in range(3)]
    long_axis = extent.index(max(extent))
    others = [i for i in range(3) if i != long_axis]
    log("%d sommets ; étendue X/Y/Z = %.1f / %.1f / %.1f ; axe long = %s" % (len(points), extent[0], extent[1], extent[2], axes[long_axis]))
    lo, hi = min(p[long_axis] for p in points), max(p[long_axis] for p in points)
    log("profil le long de %s (de %.1f à %.1f), largeurs et centres sur %s et %s :" % (axes[long_axis], lo, hi, axes[others[0]], axes[others[1]]))
    for b in range(BINS):
        a, c = lo + (hi - lo) * b / BINS, lo + (hi - lo) * (b + 1) / BINS
        chunk = [p for p in points if a <= p[long_axis] <= c]
        if len(chunk) < 3:
            continue
        log("  %s=%7.1f  larg %s=%5.2f %s=%5.2f  centre %s=%6.2f %s=%6.2f" % (
            axes[long_axis], (a + c) / 2,
            axes[others[0]], span([p[others[0]] for p in chunk]), axes[others[1]], span([p[others[1]] for p in chunk]),
            axes[others[0]], sum(p[others[0]] for p in chunk) / len(chunk), axes[others[1]], sum(p[others[1]] for p in chunk) / len(chunk)))


for asset in ASSETS:
    try:
        measure(asset)
    except Exception as error:  # noqa: BLE001 - on veut les autres mesures même si une échoue
        log("%s : échec (%s)" % (asset, error))

try:  # position du socket de la main dans le squelette nanos
    skeleton = unreal.EditorAssetLibrary.load_asset("/Game/NanosWorld/Characters/Common/SKEL_Mannequin")
    for socket in skeleton.get_editor_property("sockets"):
        name = str(socket.get_editor_property("socket_name"))
        if "hand" in name.lower():
            log("SKEL_Mannequin socket %s : os %s, position %s, rotation %s" % (
                name, socket.get_editor_property("bone_name"), socket.get_editor_property("relative_location"), socket.get_editor_property("relative_rotation")))
except Exception as error:  # noqa: BLE001
    log("sockets du squelette illisibles (%s)" % error)
log("terminé")
