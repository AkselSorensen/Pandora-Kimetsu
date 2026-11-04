"""Logotype « PANDORA KIMETSU » : des lettres angulaires dessinées au trait, tranchées par une lame.

Chaque lettre est une ou plusieurs polylignes sur une grille de 100 de haut. Le mot est dessiné deux fois, découpé le long d'une diagonale,
et les deux moitiés sont décalées : l'effet d'un coup de sabre qui a coupé le titre.
"""

LETTERS = {
    "P": [[(0, 100), (0, 0), (40, 0), (56, 12), (56, 40), (40, 52), (0, 52)]],
    "A": [[(0, 100), (22, 0), (34, 0), (56, 100)], [(13, 68), (43, 68)]],
    "N": [[(0, 100), (0, 0), (56, 100), (56, 0)]],
    "D": [[(0, 0), (0, 100), (34, 100), (56, 78), (56, 22), (34, 0), (0, 0)]],
    "O": [[(14, 0), (42, 0), (56, 14), (56, 86), (42, 100), (14, 100), (0, 86), (0, 14), (14, 0)]],
    "R": [[(0, 100), (0, 0), (40, 0), (56, 12), (56, 40), (40, 52), (0, 52)], [(26, 52), (56, 100)]],
    "K": [[(0, 0), (0, 100)], [(56, 0), (4, 54)], [(20, 38), (56, 100)]],
    "I": [[(0, 0), (0, 100)]],
    "M": [[(0, 100), (0, 0), (28, 58), (56, 0), (56, 100)]],
    "E": [[(56, 0), (0, 0), (0, 100), (56, 100)], [(0, 50), (40, 50)]],
    "T": [[(0, 0), (56, 0)], [(28, 0), (28, 100)]],
    "S": [[(56, 10), (46, 0), (10, 0), (0, 10), (0, 40), (10, 50), (46, 50), (56, 60), (56, 90), (46, 100), (10, 100), (0, 90)]],
    "U": [[(0, 0), (0, 86), (14, 100), (42, 100), (56, 86), (56, 0)]],
}


def _extent(char):
    return max(x for stroke in LETTERS[char] for x, _ in stroke)


def word_width(text, weight, gap):
    total = 0
    for char in text:
        total += (gap * 2 if char == " " else _extent(char) + weight + gap)
    return total - gap


def word(text, weight=15, gap=13):
    """Markup des lettres, origine en (0,0) = coin haut gauche de la ligne de base de la première lettre ; renvoie (markup, largeur)."""
    cursor, parts = weight / 2, []
    for char in text:
        if char == " ":
            cursor += gap * 2
            continue
        for stroke in LETTERS[char]:
            points = " ".join(f"{cursor + x:.1f},{y:.1f}" for x, y in stroke)
            parts.append(f'<polyline points="{points}"/>')
        cursor += _extent(char) + weight + gap
    return "".join(parts), word_width(text, weight, gap)


def sliced(text, x, y, height, fill, uid="lg", weight=15, gap=13, shift=(5, -3), cut=(0.3, 0.7), glow=None):
    """Titre tranché, centré en x. height : hauteur d'une lettre en pixels. Renvoie (defs, markup, largeur en pixels)."""
    scale = height / 100
    inner, width = word(text, weight, gap)
    total = width * scale
    left = x - total / 2
    top = y
    def line_y(px):
        return 100 * cut[1] + 20 + 100 * (cut[0] - cut[1]) * (px / width)

    clip_up = f"M-30 -40 H{width + 60:.0f} V{line_y(width + 60):.1f} L-30 {line_y(-30):.1f} Z"
    clip_dn = f"M-30 {line_y(-30):.1f} L{width + 60:.0f} {line_y(width + 60):.1f} V150 H-30 Z"
    # les lettres débordent de weight/2 en haut et en bas : le clip final garde la hauteur de capitale exacte
    cap = f'<clipPath id="{uid}c"><rect x="-30" y="-{weight / 2:.0f}" width="{width + 60:.0f}" height="{100 + weight:.0f}"/></clipPath>'
    defs = (
        cap
        + f'<clipPath id="{uid}u"><path d="{clip_up}"/></clipPath><clipPath id="{uid}d"><path d="{clip_dn}"/></clipPath>'
    )
    style = f'fill="none" stroke="{fill}" stroke-width="{weight}" stroke-linejoin="miter" stroke-miterlimit="10" stroke-linecap="butt"'
    sx, sy = shift
    group = lambda extra: f'<g clip-path="url(#{uid}c)"><g {style}>{extra}</g></g>'
    halves = (
        f'<g clip-path="url(#{uid}u)" transform="translate({sx} {sy})">{group(inner)}</g>'
        f'<g clip-path="url(#{uid}d)" transform="translate({-sx} {-sy})">{group(inner)}</g>'
    )
    # fil de la coupe : une ligne claire qui suit la diagonale
    x0, y0 = -10, line_y(-10)
    x1, y1 = width + 10, line_y(width + 10)
    edge = f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="#FFFFFF" stroke-width="1.6" opacity=".85"/>'
    body = f'<g transform="translate({left:.1f} {top:.1f}) scale({scale:.4f})">{halves}{edge}</g>'
    if glow:
        body = f'<g style="filter:drop-shadow(0 0 14px {glow})">{body}</g>'
    return defs, body, total
