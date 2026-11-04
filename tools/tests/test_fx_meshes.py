import importlib.util
import json
import math
import struct
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "unreal_tools" / "gen_fx_meshes.py"
spec = importlib.util.spec_from_file_location("gen_fx_meshes", SCRIPT)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def bounds(mesh):
    return [(min(p[k] for p in mesh.positions), max(p[k] for p in mesh.positions)) for k in range(3)]


@pytest.mark.parametrize("name", sorted(gen.SHAPES))
def test_every_shape_is_a_clean_mesh(name):
    mesh = gen.SHAPES[name]()
    count = len(mesh.positions)
    assert count > 8 and len(mesh.uvs) == count and len(mesh.indices) % 3 == 0 and count < 65535
    assert max(mesh.indices) < count and min(mesh.indices) >= 0
    assert all(0.0 <= u <= 1.0 and 0.0 <= v <= 1.0 for u, v in mesh.uvs)
    assert all(math.isfinite(x) for p in mesh.positions for x in p)
    extent = max(hi - lo for lo, hi in bounds(mesh))
    assert 20 < extent < 600  # entre 20 cm et 6 m : de la taille d'un coup de sabre, pas d'un decor
    # peu de triangles degeneres (les pointes d'un croissant en ont quelques-uns)
    flat = 0
    for i in range(0, len(mesh.indices), 3):
        a, b, c = (mesh.positions[mesh.indices[i + k]] for k in range(3))
        u = [b[k] - a[k] for k in range(3)]
        v = [c[k] - a[k] for k in range(3)]
        cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        flat += 1 if math.sqrt(sum(x * x for x in cross)) < 1e-6 else 0
    assert flat <= len(mesh.indices) // 3 // 10


def test_planes_and_directions_match_the_documented_frame():
    v = bounds(gen.SHAPES["SlashV"]())
    assert v[0] == (0.0, 0.0) or max(abs(x) for x in v[0]) < 1e-6  # plan YZ : x nul
    assert v[1][0] < -150 and v[1][1] > 150 and v[2][1] > 170  # ouvert gauche-droite, bombe vers le haut
    h = bounds(gen.SHAPES["SlashH"]())
    assert max(abs(x) for x in h[2]) < 1e-6 and h[0][1] > 200  # plan XY, bombe vers l'avant
    spiral = bounds(gen.SHAPES["Spiral"]())
    assert spiral[2][0] > -20 and 200 < spiral[2][1] < 260  # monte de 0 a ~2,2 m (la bande depasse un peu)
    streak = bounds(gen.SHAPES["Streak"]())
    assert streak[0][0] == 0 and streak[0][1] == 400 and max(abs(x) for x in streak[2]) < 1e-6
    dome = bounds(gen.SHAPES["Burst"]())
    assert dome[2][0] >= -1e-6 and 139 < dome[2][1] <= 140.0001


def test_crescent_tips_are_pointed_and_the_middle_is_widest():
    mesh = gen.crescent(180, 140, 36)
    widths = []
    for i in range(0, len(mesh.positions), 2):
        a, b = mesh.positions[i], mesh.positions[i + 1]
        widths.append(math.dist(a, b))
    assert widths[0] < 1e-6 and widths[-1] < 1e-6 and abs(max(widths) - 36) < 1.0
    assert widths.index(max(widths)) in range(len(widths) // 2 - 2, len(widths) // 2 + 3)


def test_gltf_files_are_consistent_and_use_the_importer_axes(tmp_path: Path):
    gen.main(["--out", str(tmp_path)])
    files = sorted(tmp_path.glob("*.gltf"))
    assert [f.stem for f in files] == sorted(f"SM_FX_{n}" for n in gen.SHAPES)
    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        blob = (tmp_path / doc["buffers"][0]["uri"]).read_bytes()
        assert len(blob) == doc["buffers"][0]["byteLength"]
        pos, nor, uv, idx = doc["accessors"]
        views = doc["bufferViews"]
        assert views[pos["bufferView"]]["byteLength"] == pos["count"] * 12 == views[nor["bufferView"]]["byteLength"]
        assert views[uv["bufferView"]]["byteLength"] == pos["count"] * 8
        assert views[idx["bufferView"]]["byteLength"] == idx["count"] * 2
        offset = views[pos["bufferView"]]["byteOffset"]
        values = struct.unpack("<%df" % (pos["count"] * 3), blob[offset: offset + pos["count"] * 12])
        xs, ys, zs = values[0::3], values[1::3], values[2::3]
        assert [min(xs), min(ys), min(zs)] == pytest.approx(pos["min"]) and [max(xs), max(ys), max(zs)] == pytest.approx(pos["max"])
        assert doc["materials"][0]["doubleSided"] is True
    # gltf (x, y, z) = Unreal (x, z, y) / 100 : le Spiral monte de ~2,2 m sur l'axe Y du glTF
    spiral = json.loads((tmp_path / "SM_FX_Spiral.gltf").read_text(encoding="utf-8"))["accessors"][0]
    assert spiral["max"][1] > 2.0 and spiral["max"][1] < 2.6
