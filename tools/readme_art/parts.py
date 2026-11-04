"""Petits éléments dessinés, communs à plusieurs images : plaques, pastilles, jauges, flèches."""
from theme import C, clipped_corners


def plate(x, y, w, h, fill, stroke, cut=14, stroke_opacity=0.7, width=1.2, extra=""):
    return f'<path d="{clipped_corners(x, y, w, h, cut)}" fill="{fill}" stroke="{stroke}" stroke-opacity="{stroke_opacity}" stroke-width="{width}" {extra}/>'


def chip(ts, x, y, text, color, size=12, h=22, tracking=1.2, filled=False, anchor="start"):
    """Pastille d'état. Renvoie (markup, largeur)."""
    w = ts.width(text, size, tracking) + 20
    x0 = x - w / 2 if anchor == "middle" else x
    fill = f'fill="{color}" fill-opacity="{0.9 if filled else 0.14}"'
    ink = "#0B0508" if filled else color
    return (
        f'<rect x="{x0:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" {fill} stroke="{color}" stroke-opacity=".8"/>'
        + ts.text(text, x0 + w / 2, y + h / 2 + size * 0.36, size, ink, anchor="middle", tracking=tracking, bold=0.15),
        w,
    )


def gauge(x, y, w, h, value, color, back="#2A1018", label=None, ts=None, delay=0.0):
    """Jauge horizontale animée (elle se remplit à l'affichage)."""
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{back}"/>'
        f'<rect x="{x}" y="{y}" width="{max(0.0, w * value):.1f}" height="{h}" rx="{h / 2}" fill="{color}" class="bar" style="animation-delay:{delay}s"/>'
    )


def arrow(x1, y1, x2, y2, color, width=2, dashed=True, head=8):
    """Flèche droite avec pointe ; en pointillés animés par défaut (le flux avance)."""
    import math

    ang = math.atan2(y2 - y1, x2 - x1)
    hx1, hy1 = x2 - head * math.cos(ang - 0.45), y2 - head * math.sin(ang - 0.45)
    hx2, hy2 = x2 - head * math.cos(ang + 0.45), y2 - head * math.sin(ang + 0.45)
    cls = ' class="dsh"' if dashed else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2 - head * 0.6 * math.cos(ang):.1f}" y2="{y2 - head * 0.6 * math.sin(ang):.1f}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"{cls}/>'
        f'<path d="M{x2:.1f} {y2:.1f} L{hx1:.1f} {hy1:.1f} L{hx2:.1f} {hy2:.1f}Z" fill="{color}"/>'
    )


def diamond(cx, cy, r, fill, stroke=None, stroke_opacity=0.8, extra=""):
    s = f' stroke="{stroke}" stroke-opacity="{stroke_opacity}" stroke-width="1.5"' if stroke else ""
    return f'<path d="M{cx} {cy - r} L{cx + r} {cy} L{cx} {cy + r} L{cx - r} {cy} Z" fill="{fill}"{s} {extra}/>'


def seal(ts, cx, cy, r, glyph, color, size=None, fill="#12070B", bold=0.6, ring=2.0):
    """Sceau rond portant un kanji (comme les techniques du HUD)."""
    size = size or r * 1.15
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{color}" stroke-width="{ring}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r - 4}" fill="none" stroke="{color}" stroke-opacity=".35" stroke-width="1"/>'
        + ts.text(glyph, cx, cy + size * 0.36, size, color, anchor="middle", bold=bold)
    )


def fmt(n):
    """Nombre à la française : espace insécable fine pour les milliers, virgule décimale."""
    if isinstance(n, float) and n != int(n):
        return f"{n:.1f}".replace(".", ",")
    n = int(n)
    return f"{n:,}".replace(",", " ")


STATUS = {
    "fait": ("FAIT", C["jade"]),
    "en cours": ("EN COURS", C["gold"]),
    "à vérifier": ("À VÉRIFIER EN JEU", C["flesh"]),
    "à faire": ("À FAIRE", "#9A8F86"),
}
