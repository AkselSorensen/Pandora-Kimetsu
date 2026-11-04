import json
from pathlib import Path

import numpy as np
import pytest

from gmod2nanos.converter import Options, convert
from gmod2nanos.gltf import source_to_gltf
from gmod2nanos.grip import GripError, apply_grip, compute_grip, is_hand_held, to_unreal
from gmod2nanos.mdl import load_mdl
from gmod2nanos.mesh import Model, SubMesh, euler_to_matrix

from . import builders

# Pose de la main dans le repère du modèle : tournée dans tous les sens, comme un os de main réel.
HAND_ROT = euler_to_matrix(np.radians(70), np.radians(-20), np.radians(35))
HAND_POS = np.array([-0.7, 13.2, 4.6])


def blade_in_hand_frame(shift: float = 0.0):
    """Un sabre dans le repère de l'os de la main, comme GMod l'enregistre : manche autour de l'origine (z de +8 à -7),
    garde à -7,5, lame vers -Z de -8 à -50, largeur sur X. Renvoie les points et les masques tranchant / dos."""
    handle = [(x, y, z) for z in np.linspace(8, -7, 12) for x in (3, 5) for y in (-1, 1)]
    guard = [(x, y, -7.5) for x in (-2, 10) for y in (-1, 1)]
    blade = [(x, y, z) for z in np.linspace(-8, -50, 10) for x in (2.5, 6.5) for y in (-0.4, 0.4)]
    points = np.array(handle + guard + blade, dtype=np.float64)
    points[:, 2] += shift
    in_blade = np.arange(len(points)) >= len(handle) + len(guard)
    return points, in_blade & (points[:, 0] > 5), in_blade & (points[:, 0] < 4), np.arange(len(handle))


def make_model(points_in_hand: np.ndarray, hand: bool = True) -> Model:
    positions = (HAND_POS + points_in_hand @ HAND_ROT.T).astype(np.float32)
    normals = np.tile((HAND_ROT @ [1.0, 0, 0]).astype(np.float32), (len(positions), 1))  # la normale suit le tranchant (X main)
    sub = SubMesh("m", positions, normals, np.zeros((len(positions), 2), np.float32), np.array([0, 1, 2], np.uint32))
    model = Model(name="SM_sword", source="models/sword.mdl", submeshes=[sub])
    if hand:
        model.hand = np.eye(4)
        model.hand[:3, :3], model.hand[:3, 3] = HAND_ROT, HAND_POS
    return model


def test_to_unreal_matches_gltf_writer_and_importer():
    # mesuré sur un .uexp cuit : l'importeur d'Unreal 5.7 convertit le glTF avec UE = (x, z, y)
    v = np.array([[1.0, 2.0, 3.0]])
    g = source_to_gltf(v)
    importer = np.stack([g[:, 0], g[:, 2], g[:, 1]], axis=1)
    np.testing.assert_allclose(importer, to_unreal(v))


def test_blade_is_oriented_for_nanos():
    points, edge, spine, handle = blade_in_hand_frame()
    model = make_model(points)
    grip = compute_grip(model, scale=0.0254)
    apply_grip(model, grip)
    ue = to_unreal(model.submeshes[0].positions)  # le mesh tel que le moteur le voit après l'importeur

    assert (grip.kind, grip.method, grip.warnings) == ("blade", "hand-bone", [])
    assert grip.handling == "SingleHandedMelee"
    assert grip.length_cm == pytest.approx(58 * 2.54, rel=1e-6)
    # lame vers +Z (50 unités devant la main), pommeau derrière (8) : comme le Katana_sword de nanos
    assert ue[:, 2].max() == pytest.approx(50, abs=1e-3) and ue[:, 2].min() == pytest.approx(-8, abs=1e-3)
    # poignée à l'origine : la section du manche est centrée sur X = Y = 0
    slab = ue[handle][np.abs(ue[handle][:, 2]) < 1]
    assert (slab[:, 0].min() + slab[:, 0].max()) / 2 == pytest.approx(0, abs=1e-3)
    assert (slab[:, 1].min() + slab[:, 1].max()) / 2 == pytest.approx(0, abs=1e-3)
    # tranchant (côté +X de la main) vers +X, dos vers -X
    assert ue[edge][:, 0].mean() > ue[spine][:, 0].mean() + 3
    # la lame est plate : sa largeur est sur X, son épaisseur (plats vers ±Y) sur Y
    blade = ue[edge | spine]
    assert np.ptp(blade[:, 0]) > 3 and np.ptp(blade[:, 1]) < 1


def test_rotation_is_proper_and_normals_follow():
    points, *_ = blade_in_hand_frame()
    model = make_model(points)
    grip = compute_grip(model)
    assert np.linalg.det(grip.rotation) == pytest.approx(1)  # pas de miroir : l'ordre des triangles reste valable
    np.testing.assert_allclose(grip.rotation @ grip.rotation.T, np.eye(3), atol=1e-9)
    apply_grip(model, grip)
    # la normale pointait vers le tranchant : dans Unreal elle pointe maintenant vers +X
    np.testing.assert_allclose(to_unreal(model.submeshes[0].normals)[0], [1, 0, 0], atol=1e-5)


def test_tip_is_the_end_farthest_from_the_hand():
    points, *_ = blade_in_hand_frame(shift=45)  # la main est maintenant près de l'ancienne pointe (z -50 devient -5)
    model = make_model(points)
    apply_grip(model, compute_grip(model))
    p = to_unreal(model.submeshes[0].positions)
    assert p[:, 2].max() == pytest.approx(53, abs=1e-3)  # l'ancien pommeau, à 53 de la main, est maintenant devant


def test_firearm_is_not_handled():
    points, *_ = blade_in_hand_frame()
    model = make_model(points)
    model.attachments["muzzle"] = np.eye(4)
    with pytest.raises(GripError, match="arme à feu"):
        compute_grip(model)


def test_compact_shape_is_rejected():
    cube = np.array([(x, y, z) for x in (-2.5, 2.5) for y in (-2.5, 2.5) for z in (-3, 3)], dtype=np.float64)
    with pytest.raises(GripError, match="compacte"):
        compute_grip(make_model(cube))


def test_hand_must_be_on_the_weapon():
    points, *_ = blade_in_hand_frame(shift=200)
    with pytest.raises(GripError, match="main"):
        compute_grip(make_model(points))


def test_without_hand_bone_the_model_origin_stands_for_the_hand():
    # lame le long de +Y, manche à l'origine : aucun os de main
    points = np.array([(x, y, z) for y in np.linspace(-8, 50, 14) for x in (-2, 2) for z in (-0.5, 0.5)], dtype=np.float64)
    sub = SubMesh("m", points.astype(np.float32), np.zeros((len(points), 3), np.float32), np.zeros((len(points), 2), np.float32), np.array([0, 1, 2], np.uint32))
    model = Model(name="SM_x", source="models/x.mdl", submeshes=[sub])
    grip = compute_grip(model)
    apply_grip(model, grip)
    assert grip.method == "origin" and any("origine" in w for w in grip.warnings)
    assert to_unreal(model.submeshes[0].positions)[:, 2].max() == pytest.approx(50, abs=1e-3)


def test_mdl_exposes_hand_bone_and_attachments(tmp_path: Path):
    files = {
        "models/w/sword.mdl": builders.build_mdl(
            bones=[("ValveBiped.Bip01_R_Hand", -1, (1.0, 2.0, 3.0))], attachments=[("muzzle", 0, (5.0, 0.0, 0.0))]
        ),
        "models/w/sword.vvd": builders.build_vvd(),
        "models/w/sword.dx90.vtx": builders.build_vtx(),
    }
    for name, data in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(data)
    model, _ = load_mdl(tmp_path / "models/w/sword.mdl", "SM_sword", "models/w/sword.mdl")
    assert is_hand_held(model)
    np.testing.assert_allclose(model.hand[:3, 3], [1, 2, 3], atol=1e-5)
    np.testing.assert_allclose(model.attachments["muzzle"][:3, 3], [6, 2, 3], atol=1e-5)  # position de l'os + local


def test_model_without_hand_bone_is_not_hand_held():
    model = Model(name="SM_chair", source="models/chair.mdl")
    assert not is_hand_held(model)


def _sword_addon() -> dict[str, bytes]:
    """Un sabre lié à l'os de la main, à l'origine, dont la lame (quad de 5 sur 60) part vers -Z."""
    blade = [(2, 0, 10), (7, 0, 10), (7, 0, -50), (2, 0, -50)]
    return {
        "models/w/sword.mdl": builders.build_mdl(bones=[("ValveBiped.Bip01_R_Hand", -1, (0, 0, 0))]),
        "models/w/sword.vvd": builders.build_vvd(positions=blade),
        "models/w/sword.dx90.vtx": builders.build_vtx(),
        "materials/models/test/chair_wood.vmt": builders.build_vmt("models/test/chair_wood_diffuse"),
        "materials/models/test/chair_wood_diffuse.vtf": builders.build_vtf(),
    }


def _write(root: Path, files: dict[str, bytes]) -> None:
    for name, data in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(data)


def _position_bounds(gltf_path: Path):
    doc = json.loads(gltf_path.read_text())
    acc = doc["accessors"][doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
    return acc["min"], acc["max"]


def test_convert_orients_hand_held_weapon(tmp_path: Path):
    _write(tmp_path / "addon", _sword_addon())
    rep = convert([tmp_path / "addon"], tmp_path / "out", Options(title="Sabres"), lambda m: None)
    out = tmp_path / "out"
    assert rep.errors == []
    (entry,) = rep.static_meshes
    assert entry["grip"]["kind"] == "blade" and entry["grip"]["handling"] == "SingleHandedMelee"

    # glTF y = lame de l'arme après l'importeur d'Unreal (UE Z = glTF y). Pointe à +50 unités, pommeau à -10.
    low, high = _position_bounds(out / "1-unreal/Sabres/Models/SM_sword/SM_sword.gltf")
    assert high[1] == pytest.approx(50 * 0.0254, abs=1e-5) and low[1] == pytest.approx(-10 * 0.0254, abs=1e-5)

    weapons = json.loads((out / "weapons.json").read_text())
    assert weapons[0]["asset"] == "sabres::SM_sword" and weapons[0]["handling"] == "SingleHandedMelee"

    # package de test : une vraie prise en main (Melee + PickUp), plus d'attache manuelle à un os
    lua = (out / "3-package-test/sabres-test/Server/Index.lua").read_text()
    assert 'asset = "sabres::SM_sword"' in lua and "Melee(" in lua and "SetAttachmentSettings" in lua and "PickUp" in lua
    assert 'AttachTo(holder, "hand_r")' not in lua
    client = (out / "3-package-test/sabres-test/Client/Index.lua").read_text()
    assert '"sabres:weapon"' in client and "Reliability.Reliable" in client


def test_convert_can_leave_weapons_untouched(tmp_path: Path):
    _write(tmp_path / "addon", _sword_addon())
    rep = convert([tmp_path / "addon"], tmp_path / "out", Options(title="Sabres", hold_weapons=False), lambda m: None)
    assert "grip" not in rep.static_meshes[0]
    low, high = _position_bounds(tmp_path / "out/1-unreal/Sabres/Models/SM_sword/SM_sword.gltf")
    assert high[2] == pytest.approx(0.0254 * 7, abs=1e-5)  # glTF Z = X Source, inchangé
