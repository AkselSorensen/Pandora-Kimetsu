"""Génère des meshes d'effet originaux (croissants de coup, anneaux, spirales, vent, éclair, griffes, dôme) en glTF.

    python unreal_tools/gen_fx_meshes.py            # écrit fx_meshes/SM_FX_<nom>.gltf + .bin

Chaque mesh est un ruban : les UV donnent u le long de la forme (0 à 1) et v en travers (0 bord intérieur, 1 bord extérieur). Le matériau
lumineux M_FX_Glow (unreal_tools/import_fx_meshes.py) s'en sert pour estomper les bords et les pointes. Tout est dessiné par code, sans
aucune donnée venant d'un autre jeu.

Repère : les formes sont décrites en repère Unreal, en centimètres (avant = +X, droite = +Y, haut = +Z), comme les effets de wakfu-rp les
placent devant le lanceur. L'import glTF d'Unreal 5.7 envoie le glTF (x, y, z) sur Unreal (x, z, y) et multiplie les mètres par 100 : on écrit
donc le glTF (x, z, y) / 100. Ce changement de repère inverse l'orientation des triangles : le matériau est double face.
"""
import argparse
import json
import math
import struct
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "fx_meshes"
SEGMENTS = 48  # échantillons le long d'une forme


class Mesh:
    """Sommets (x, y, z en cm, Unreal), UV et triangles."""

    def __init__(self):
        self.positions: list[tuple[float, float, float]] = []
        self.uvs: list[tuple[float, float]] = []
        self.indices: list[int] = []

    def ribbon(self, samples, closed=False):
        """samples : [(centre, direction vers l'extérieur, demi-largeur)] ; deux sommets par échantillon, v = 0 puis 1."""
        base = len(self.positions)
        count = len(samples)
        for i, (centre, direction, half) in enumerate(samples):
            u = i / (count - 1)
            self.positions.append(tuple(c - d * half for c, d in zip(centre, direction)))
            self.uvs.append((u, 0.0))
            self.positions.append(tuple(c + d * half for c, d in zip(centre, direction)))
            self.uvs.append((u, 1.0))
        for i in range(count - 1):
            a, b, c, d = base + 2 * i, base + 2 * i + 1, base + 2 * i + 2, base + 2 * i + 3
            self.indices += [a, b, c, b, d, c]
        return self

    def merge(self, other, offset=(0.0, 0.0, 0.0)):
        base = len(self.positions)
        self.positions += [tuple(p + o for p, o in zip(point, offset)) for point in other.positions]
        self.uvs += other.uvs
        self.indices += [base + i for i in other.indices]
        return self


def taper(t, power=0.8):
    """0 aux deux pointes, 1 au milieu."""
    return math.sin(math.pi * t) ** power


def crescent(radius, span_deg, width, plane="YZ"):
    """Croissant dont le bord extérieur est un arc de cercle et dont la largeur s'annule aux pointes.

    YZ : dans le plan vertical perpendiculaire à l'avant (on le voit de dos), l'arc bombe vers le haut, de la gauche vers la droite.
    XY : dans le plan horizontal, l'arc bombe vers l'avant (+X), de la gauche vers la droite.
    """
    samples = []
    for i in range(SEGMENTS + 1):
        t = i / SEGMENTS
        angle = math.radians(-span_deg / 2 + span_deg * t)
        half = width * taper(t) / 2
        direction = (0.0, math.sin(angle), math.cos(angle)) if plane == "YZ" else (math.cos(angle), math.sin(angle), 0.0)
        centre = tuple(d * (radius - half) for d in direction)
        samples.append((centre, direction, half))
    return Mesh().ribbon(samples)


def annulus(outer, inner):
    samples = []
    for i in range(SEGMENTS + 1):
        angle = 2 * math.pi * i / SEGMENTS
        direction = (math.cos(angle), math.sin(angle), 0.0)
        centre = tuple(d * (outer + inner) / 2 for d in direction)
        samples.append((centre, direction, (outer - inner) / 2))
    return Mesh().ribbon(samples)


def helix(radius_start, radius_end, height, turns, band):
    """Bande verticale qui s'enroule en montant ; ses extrémités s'effilent."""
    samples = []
    for i in range(SEGMENTS * 2 + 1):
        t = i / (SEGMENTS * 2)
        angle = 2 * math.pi * turns * t
        radius = radius_start + (radius_end - radius_start) * t
        samples.append(((radius * math.cos(angle), radius * math.sin(angle), height * t), (0.0, 0.0, 1.0), band * taper(t, 0.7) / 2))
    return Mesh().ribbon(samples)


def streak(length, width):
    """Lentille couchée le long de l'avant, pour une botte ou un éclair."""
    samples = [((length * i / SEGMENTS, 0.0, 0.0), (0.0, 1.0, 0.0), width * taper(i / SEGMENTS, 0.6) / 2) for i in range(SEGMENTS + 1)]
    return Mesh().ribbon(samples)


def claws():
    mesh = Mesh()
    for y in (-34.0, 0.0, 34.0):
        mesh.merge(crescent(150, 100, 10), (0.0, y, 0.0))
    return mesh


def dome(radius, rings=12):
    """Demi-sphère creuse : u autour, v de la base (0) au sommet (1)."""
    mesh = Mesh()
    columns = SEGMENTS
    for r in range(rings + 1):
        v = r / rings
        elevation = v * math.pi / 2
        for c in range(columns + 1):
            angle = 2 * math.pi * c / columns
            mesh.positions.append((radius * math.cos(elevation) * math.cos(angle), radius * math.cos(elevation) * math.sin(angle), radius * math.sin(elevation)))
            mesh.uvs.append((c / columns, v))
    for r in range(rings):
        for c in range(columns):
            a = r * (columns + 1) + c
            b, d = a + 1, a + columns + 1
            mesh.indices += [a, b, d, b, d + 1, d]
    return mesh


# nom -> mesh : voir le docstring pour le repère. Les noms servent d'identifiants dans Unreal (SM_FX_<nom>) et dans wakfu-rp (VfxPlan.lua).
SHAPES = {
    "SlashV": lambda: crescent(180, 140, 36),
    "SlashThin": lambda: crescent(240, 160, 12),
    "SlashWide": lambda: crescent(170, 120, 70),
    "SlashH": lambda: crescent(210, 200, 40, "XY"),
    "Wave": lambda: crescent(130, 110, 55, "XY"),
    "Ring": lambda: annulus(150, 135),
    "RingWide": lambda: annulus(150, 30),
    "Spiral": lambda: helix(90, 90, 220, 2.5, 28),
    "Wind": lambda: helix(40, 120, 260, 3, 18),
    "Streak": lambda: streak(400, 28),
    "Claw": claws,
    "Burst": lambda: dome(140),
}


def normals_of(mesh: Mesh):
    """Normales de sommet (moyenne des faces), en repère Unreal."""
    acc = [[0.0, 0.0, 0.0] for _ in mesh.positions]
    for i in range(0, len(mesh.indices), 3):
        a, b, c = (mesh.positions[mesh.indices[i + k]] for k in range(3))
        u = tuple(b[k] - a[k] for k in range(3))
        v = tuple(c[k] - a[k] for k in range(3))
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        for k in range(3):
            for index in mesh.indices[i:i + 3]:
                acc[index][k] += n[k]
    result = []
    for n in acc:
        length = math.sqrt(sum(x * x for x in n)) or 1.0
        result.append(tuple(x / length for x in n))
    return result


def to_gltf_space(point):
    """Unreal (x, y, z) en cm -> glTF (x, z, y) en mètres."""
    x, y, z = point
    return (x / 100.0, z / 100.0, y / 100.0)


def to_gltf_normal(normal):
    x, y, z = normal
    return (x, z, y)


def write(name: str, mesh: Mesh, folder: Path):
    """Écrit SM_FX_<name>.gltf et .bin dans folder ; renvoie le chemin du .gltf."""
    stem = f"SM_FX_{name}"
    positions = [to_gltf_space(p) for p in mesh.positions]
    normals = [to_gltf_normal(n) for n in normals_of(mesh)]
    blob = bytearray()
    views = []

    def add(data: bytes, target):
        while len(blob) % 4:
            blob.append(0)
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob.extend(data)
        return len(views) - 1

    pos_view = add(b"".join(struct.pack("<3f", *p) for p in positions), 34962)
    nor_view = add(b"".join(struct.pack("<3f", *n) for n in normals), 34962)
    uv_view = add(b"".join(struct.pack("<2f", *uv) for uv in mesh.uvs), 34962)
    idx_view = add(b"".join(struct.pack("<H", i) for i in mesh.indices), 34963)
    count = len(positions)
    doc = {
        "asset": {"version": "2.0", "generator": "gen_fx_meshes.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": stem}],
        "meshes": [{"name": stem, "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3, "material": 0, "mode": 4}]}],
        "materials": [{"name": "M_FX_Placeholder", "doubleSided": True, "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0, "roughnessFactor": 1}}],
        "accessors": [
            {"bufferView": pos_view, "componentType": 5126, "count": count, "type": "VEC3",
             "min": [min(p[k] for p in positions) for k in range(3)], "max": [max(p[k] for p in positions) for k in range(3)]},
            {"bufferView": nor_view, "componentType": 5126, "count": count, "type": "VEC3"},
            {"bufferView": uv_view, "componentType": 5126, "count": count, "type": "VEC2"},
            {"bufferView": idx_view, "componentType": 5123, "count": len(mesh.indices), "type": "SCALAR"},
        ],
        "bufferViews": views,
        "buffers": [{"uri": stem + ".bin", "byteLength": len(blob)}],
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (stem + ".bin")).write_bytes(bytes(blob))
    path = folder / (stem + ".gltf")
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=OUT, help="dossier de sortie (défaut : fx_meshes/ à la racine du dépôt)")
    args = ap.parse_args(argv)
    for name, build in SHAPES.items():
        mesh = build()
        path = write(name, mesh, args.out)
        print(f"{path.name} : {len(mesh.positions)} sommets, {len(mesh.indices) // 3} triangles")


if __name__ == "__main__":
    main()
