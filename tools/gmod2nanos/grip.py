"""Prise en main des armes GMod : repère dans lequel un personnage nanos world tient une arme.

Un modèle d'arme GMod (world model) est lié à l'os de la main droite du joueur (ValveBiped.Bip01_R_Hand) : sa géométrie est
décrite dans le repère de cet os, ce qui fixe le sens de la lame, le côté du tranchant et l'endroit de la poignée. nanos world
attend, comme pour ses armes natives (couteau, pied de biche...), un mesh dont l'origine est à la poignée, la pointe vers +X et
le haut vers +Z : tenu ainsi, il n'a besoin d'aucun réglage d'os ni de socket.

`compute_grip` calcule la transformation entre les deux et `apply_grip` la fixe dans le mesh exporté.

Mesuré sur 176 armes blanches d'un même addon : l'axe long de l'arme est l'axe Z de l'os de la main (175 sur 176), la pointe
est vers -Z, la largeur de la lame sur X et le tranchant du côté +X (les 17 katanas se courbent toutes vers -X, côté du dos).
Les armes à feu (point `muzzle`) ne sont pas gérées ici : leur repère de main est différent.

Conversion d'axes de l'importeur glTF d'Unreal 5.7, mesurée en retrouvant les sommets d'un glTF dans son .uexp cuit : UE =
(glTF.x, glTF.z, glTF.y). Pour un point Source écrit par `gltf.source_to_gltf` (glTF = (Y, Z, X)) cela donne UE = (Y, X, Z) :
sans correction l'avant de l'arme arrive sur +Y d'Unreal, soit sur le côté du personnage (ce n'est pas la conversion que
supposait retarget.py). Le mesh exporté est donc précompensé : il sort de l'importeur directement dans `UNREAL_FRAME`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .gltf import DEFAULT_SCALE
from .mesh import Model

def to_unreal(points: np.ndarray) -> np.ndarray:
    """Points exportés (espace Source) -> repère Unreal après l'importeur glTF : (X, Y, Z) devient (Y, X, Z)."""
    return np.stack([points[:, 1], points[:, 0], points[:, 2]], axis=1)


# Repère voulu dans Unreal, celui du Katana_sword de nanos (pack aksel-animations), bien tenu sans aucun réglage : mesuré dans
# Unreal avec unreal_tools/measure_weapon_frames.py, boîte (-4.8, -4.4, -27.2) à (4.9, 4.4, 105.1), donc lame vers +Z (manche de
# -27 à +2, garde vers Z = 6), largeur sur X, plats sur ±Y ; la lame se courbe vers +X à mi-longueur : +X est le côté convexe,
# donc le tranchant, et -X le dos.
# EXPORT part du repère de prise (avant X, gauche Y, haut Z = dos, tranchant vers le bas) et renvoie l'espace Source à écrire
# pour qu'après `to_unreal` on obtienne ce repère : avant -> Source +Z -> Unreal +Z ; tranchant (-Z) -> Source +Y -> Unreal +X.
EXPORT = np.array([[0.0, -1.0, 0.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
EDGE_IN_HAND = np.array([1.0, 0.0, 0.0])  # côté du tranchant dans le repère de l'os de la main (X)
BLADE_AXIS_IN_HAND = 2  # axe de la lame dans le repère de l'os de la main (Z)
BLADE_DOMINANCE = 1.25  # étendue selon l'axe de la lame, au moins ce multiple de la plus grande des deux autres
MIN_ELONGATION = 2.5  # longueur / largeur minimale d'une arme blanche (un pistolet est autour de 1,5)
HANDLING = "SingleHandedMelee"


class GripError(ValueError):
    """Le modèle ne se prête pas au calcul : il est exporté sans correction."""


@dataclass
class Grip:
    """Transformation v' = rotation @ (v - origin) du repère du modèle GMod vers l'espace Source à écrire (voir EXPORT)."""

    kind: str
    rotation: np.ndarray  # 3x3, rotation propre (ordre des triangles conservé)
    origin: np.ndarray  # point du modèle placé à l'origine : le centre de la poignée
    length_cm: float
    handling: str  # HandlingMode nanos conseillé
    method: str  # "hand-bone" (os de la main) ou "origin" (origine du modèle prise pour la main)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "handling": self.handling,
            "length_cm": round(self.length_cm, 1),
            "method": self.method,
            "warnings": self.warnings,
        }


def is_hand_held(model: Model) -> bool:
    """Modèle lié à l'os de la main droite, à un ou deux os : un world model d'arme, pas un playermodel complet."""
    return model.hand is not None and model.bone_count <= 2


def _points(model: Model) -> np.ndarray:
    if not model.submeshes:
        raise GripError("aucun sommet")
    return np.concatenate([s.positions for s in model.submeshes]).astype(np.float64)


def compute_grip(model: Model, scale: float = DEFAULT_SCALE) -> Grip:
    """Prise d'une arme blanche (épée, katana, lance...). Lève GripError si le modèle n'en est pas une."""
    if "muzzle" in model.attachments:
        raise GripError("arme à feu (point muzzle) : prise en main non gérée")
    points = _points(model)
    if model.hand is not None:
        hand_pos, hand_rot, method = model.hand[:3, 3], model.hand[:3, :3], "hand-bone"
    else:
        hand_pos, hand_rot, method = np.zeros(3), np.eye(3), "origin"
    h = (points - hand_pos) @ hand_rot  # géométrie dans le repère de la main

    warnings: list[str] = []
    extent = np.ptp(h, axis=0)
    # Convention de l'os de la main : l'arme y est tenue en lame si c'est selon son axe Z qu'elle s'étend le plus (même avec une
    # garde ou une tête massive, qui fausseraient une analyse en composantes principales).
    held_like_a_blade = method == "hand-bone" and extent[BLADE_AXIS_IN_HAND] >= BLADE_DOMINANCE * np.delete(extent, BLADE_AXIS_IN_HAND).max()
    if held_like_a_blade:
        long_axis = np.eye(3)[BLADE_AXIS_IN_HAND]
        edge = EDGE_IN_HAND
    else:
        _, _, axes = np.linalg.svd(h - h.mean(axis=0), full_matrices=False)
        long_axis, wide_axis = axes[0], axes[1]
        if np.ptp(h @ long_axis) / max(np.ptp(h @ wide_axis), 1e-9) < MIN_ELONGATION:
            raise GripError("forme trop compacte pour une arme blanche")
        lateral = h @ wide_axis
        heavy_side = 1.0 if lateral.mean() >= (lateral.max() + lateral.min()) / 2 else -1.0  # le dos est plus massif
        edge = -heavy_side * wide_axis
        warnings.append("orientation estimée d'après la forme du modèle (l'arme n'est pas tenue en lame par l'os de la main)")
    if method == "origin":
        warnings.append("pas d'os de main : l'origine du modèle est prise pour la main")

    along = h @ long_axis
    length = float(along.max() - along.min())
    if abs(along.max()) < abs(along.min()):  # la pointe est le bout le plus éloigné de la main
        long_axis, along = -long_axis, -along
    if not along.min() - 0.1 * length <= 0 <= along.max() + 0.1 * length:
        raise GripError("la main n'est pas sur l'arme")

    forward = long_axis
    edge = edge - (edge @ forward) * forward
    edge /= np.linalg.norm(edge)
    up = -edge  # tranchant vers le bas, dos vers le haut, comme le couteau de nanos
    left = np.cross(up, forward)
    to_grip = EXPORT @ np.stack([forward, left, up])  # repère de prise exprimé dans le repère de la main, précompensé

    # Origine : centre de la section de la poignée, à hauteur de la main le long de la lame.
    across = h - np.outer(along, long_axis)
    near = np.abs(along) <= 0.04 * length
    if np.count_nonzero(near) < 8:
        near = np.zeros(len(along), dtype=bool)
        near[np.argsort(np.abs(along))[:8]] = True
    slab = across[near]
    grip_in_hand = (slab.min(axis=0) + slab.max(axis=0)) / 2

    return Grip(
        kind="blade",
        rotation=to_grip @ hand_rot.T,
        origin=hand_pos + hand_rot @ grip_in_hand,
        length_cm=length * scale * 100,
        handling=HANDLING,
        method=method,
        warnings=warnings,
    )


def apply_grip(model: Model, grip: Grip) -> None:
    """Fixe la prise dans le mesh : l'origine du modèle devient la poignée ; après l'importeur d'Unreal, la lame va vers +Z."""
    for sm in model.submeshes:
        sm.positions = np.ascontiguousarray((sm.positions - grip.origin) @ grip.rotation.T, dtype=np.float32)
        sm.normals = np.ascontiguousarray(sm.normals @ grip.rotation.T, dtype=np.float32)
