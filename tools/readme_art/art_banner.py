"""Bannière d'accueil, logo carré et rangée d'écussons."""
import math

from glyphs import Typeset
from logotype import sliced
from theme import C, clipped_corners, grad, ink_filter, patterns, petals, radial, svg_doc


def sun(cx, cy, r, ray=16):
    """Soleil à rayons, pour le camp des pourfendeurs : le seul vrai danger des démons."""
    rays = []
    for i in range(ray):
        a = math.tau * i / ray
        a1, a2 = a - 0.09, a + 0.09
        r0, r1 = r * 1.18, r * (2.05 if i % 2 == 0 else 1.62)
        pts = [(cx + math.cos(a1) * r0, cy + math.sin(a1) * r0), (cx + math.cos(a) * r1, cy + math.sin(a) * r1), (cx + math.cos(a2) * r0, cy + math.sin(a2) * r0)]
        rays.append("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r * 2.6:.0f}" fill="url(#haloSun)" class="glw"/>'
        f'<path d="{"".join(rays)}" fill="{C["gold"]}" opacity=".85" class="spin"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#sunGrad)"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r * 0.72:.1f}" fill="none" stroke="#FFF3B0" stroke-opacity=".5" stroke-width="1.5"/>'
    )


def moon(cx, cy, r):
    """Lune de sang : elle bat comme un cœur."""
    craters = "".join(f'<circle cx="{cx + dx}" cy="{cy + dy}" r="{rr}" fill="#5A0A16" opacity=".22"/>' for dx, dy, rr in ((-12, -10, 9), (14, 8, 7), (-6, 16, 5), (10, -18, 4)))
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r * 2.7:.0f}" fill="url(#haloMoon)" class="hb"/>'
        f'<g class="hb"><circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#moonGrad)"/>{craters}'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{C["bright"]}" stroke-opacity=".55" stroke-width="1.5"/></g>'
    )


def sky_defs():
    return (
        grad("bg", [(0, "#07040A", None), (0.55, "#12070B", None), (1, "#1B0A0F", None)])
        + radial("glowBlue", [(0, C["slayer"], 0.42), (1, C["slayer"], 0)], 0.12, 0.88, 0.62)
        + radial("glowRed", [(0, C["blood"], 0.5), (1, C["blood"], 0)], 0.88, 0.88, 0.62)
        + radial("sunGrad", [(0, "#FFF6C2", None), (0.55, C["gold"], None), (1, "#E0902A", None)], 0.4, 0.38, 0.75)
        + radial("haloSun", [(0, C["gold"], 0.35), (1, C["gold"], 0)])
        + radial("moonGrad", [(0, "#F6C9AE", None), (0.55, "#C9485A", None), (1, "#7E0F20", None)], 0.38, 0.35, 0.78)
        + radial("haloMoon", [(0, C["blood"], 0.55), (1, C["blood"], 0)])
    )


def mountains(w, h, top1, top2):
    far = f"M0 {top1} L90 {top1 - 30} L170 {top1 - 8} L260 {top1 - 50} L350 {top1 - 12} L430 {top1 - 34} L520 {top1} L610 {top1 - 38} L700 {top1 - 10} L790 {top1 - 45} L880 {top1 - 12} L1000 {top1 - 34} V{h} H0Z"
    near = f"M0 {top2} L120 {top2 - 32} L220 {top2 - 6} L330 {top2 - 42} L450 {top2 - 4} L560 {top2 - 34} L690 {top2} L800 {top2 - 36} L920 {top2 - 6} L1000 {top2 - 26} V{h} H0Z"
    return f'<path d="{far}" fill="#0E0610"/><path d="{near}" fill="#08040B"/>'


def banner():
    ts = Typeset()
    W, H = 1000, 420
    title_defs, title_body, _ = sliced("PANDORA KIMETSU", 500, 150, 70, C["ivory"], uid="bt", weight=15, gap=13, glow=C["blood"])
    petal_markup, petal_css = petals(26, W, H, seed=11)
    sub = "MODE DE JEU DE RÔLE  ·  DEMON SLAYER  ·  NANOS WORLD"
    sub_w = ts.width(sub, 15, 5)
    defs = (
        sky_defs() + patterns() + ink_filter() + title_defs
        + f'<g id="titleShape">{title_body}</g>'
        + '<mask id="titleMask" maskUnits="userSpaceOnUse" x="0" y="0" width="1000" height="420"><use href="#titleShape"/></mask>'
        + '<linearGradient id="glint" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".95"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        + '<linearGradient id="slashG" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="420"><stop offset="0" stop-color="#EFE3D0" stop-opacity="0"/><stop offset=".45" stop-color="#EFE3D0" stop-opacity=".9"/><stop offset="1" stop-color="#EFE3D0" stop-opacity="0"/></linearGradient>'
        + '<linearGradient id="stripFade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>'
        + '<mask id="stripMask" maskUnits="userSpaceOnUse" x="0" y="360" width="1000" height="60"><rect x="0" y="360" width="1000" height="60" fill="url(#stripFade)"/></mask>'
    )
    body = []
    body.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#glowBlue)"/><rect width="{W}" height="{H}" fill="url(#glowRed)"/>')
    body.append(ts.text("鬼滅", 500, 338, 330, C["ivory"], anchor="middle", tracking=26, opacity=0.05, extra='filter="url(#ink)"'))
    body.append(mountains(W, H, 332, 374))
    body.append(sun(150, 118, 40) + moon(850, 118, 40))
    body.append(f'<g mask="url(#stripMask)"><polygon points="0,372 530,372 488,420 0,420" fill="url(#ichi-slayer)"/><polygon points="530,372 1000,372 1000,420 488,420" fill="url(#ichi-demon)"/></g>')
    body.append(f'<line x1="540" y1="-10" x2="462" y2="430" stroke="url(#slashG)" stroke-width="1.6"/>')
    body.append(f'<g>{petal_markup}</g>')
    body.append('<use href="#titleShape"/>')
    body.append('<g mask="url(#titleMask)"><g transform="skewX(-24)"><rect class="sweep" x="0" y="140" width="130" height="100" fill="url(#glint)" style="animation:sweep 7s ease-in-out infinite"/></g></g>')
    sx = 500 - sub_w / 2
    body.append(ts.text(sub, 500, 276, 15, C["ivory"], anchor="middle", tracking=5, opacity=0.78))
    body.append(f'<path d="M{sx - 52} 270 h40 M{sx + sub_w + 12} 270 h40" stroke="{C["blood"]}" stroke-width="1.5"/><path d="M{sx - 6} 270 l-6 -4 l-6 4 l6 4Z M{sx + sub_w + 6} 270 l6 -4 l6 4 l-6 4Z" fill="{C["blood"]}"/>')
    body.append(ts.text("Deux camps. Une seule nuit. Choisis ton souffle… ou ton sang.", 500, 322, 23, C["ivory"], anchor="middle", bold=0.2))
    body.append(f'<path d="{clipped_corners(8, 8, 984, 404, 18)}" fill="none" stroke="{C["blood"]}" stroke-opacity=".4" stroke-width="1.2"/>')
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "Pandora Kimetsu",
                   "Bannière : le titre Pandora Kimetsu tranché par une lame, un soleil à gauche pour les pourfendeurs, une lune de sang à droite pour les démons, des pétales de glycine qui tombent.",
                   style=petal_css)


def logo():
    """Emblème carré : disque solaire et lune de sang séparés par la lame, au centre le kanji du démon."""
    ts = Typeset()
    S = 400
    defs = (
        sky_defs() + ink_filter()
        + '<clipPath id="disc"><circle cx="200" cy="200" r="150"/></clipPath>'
        + '<clipPath id="left"><polygon points="0,0 232,0 168,400 0,400"/></clipPath>'
        + '<clipPath id="right"><polygon points="232,0 400,0 400,400 168,400"/></clipPath>'
    )
    body = [
        f'<rect width="{S}" height="{S}" rx="48" fill="url(#bg)"/>',
        f'<g clip-path="url(#disc)"><g clip-path="url(#left)"><rect width="400" height="400" fill="#0B2230"/><circle cx="130" cy="140" r="170" fill="{C["slayer"]}" opacity=".35"/></g>'
        f'<g clip-path="url(#right)"><rect width="400" height="400" fill="#240810"/><circle cx="290" cy="270" r="170" fill="{C["blood"]}" opacity=".45"/></g></g>',
        f'<circle cx="200" cy="200" r="150" fill="none" stroke="{C["ivory"]}" stroke-opacity=".75" stroke-width="3"/>',
        f'<circle cx="200" cy="200" r="132" fill="none" stroke="{C["blood"]}" stroke-opacity=".6" stroke-width="1.5" stroke-dasharray="3 7"/>',
        f'<line x1="238" y1="40" x2="162" y2="360" stroke="{C["ivory"]}" stroke-width="5" stroke-linecap="round"/>',
        f'<line x1="238" y1="40" x2="162" y2="360" stroke="#fff" stroke-opacity=".6" stroke-width="1.5" stroke-linecap="round"/>',
        ts.text("鬼", 200, 262, 190, C["ivory"], anchor="middle", bold=2, extra='filter="url(#ink)"'),
    ]
    defs += ts.defs()
    return svg_doc(S, S, "".join(body), defs, "Logo Pandora Kimetsu", "Un disque coupé en biais par une lame : le bleu du soleil des pourfendeurs à gauche, le rouge de la lune des démons à droite, et le kanji 鬼 (démon) au centre.")


def badges():
    """Rangée d'écussons sous la bannière (faits réels du dépôt)."""
    ts = Typeset()
    items = [
        ("nanos world", "Lua 5.4", C["slayer"]),
        ("Unreal", "5.7", C["ivory"]),
        ("voies", "8", C["gold"]),
        ("lames", "176", C["jade"]),
        ("effets Niagara", "63", C["soul"]),
        ("tests de simulation", "6 suites", C["flesh"]),
        ("issues", "61", C["blood"]),
        ("projet de fan", "sans lien officiel", C["stone"]),
    ]
    x, gap, y, h, size = 0, 10, 4, 32, 14
    parts = []
    for left, right, color in items:
        lw, rw = ts.width(left, size, 0.5) + 24, ts.width(right, size, 0.5) + 24
        parts.append(
            f'<g transform="translate({x} {y})"><path d="{clipped_corners(0, 0, lw + rw, h, 7)}" fill="#12070B" stroke="{color}" stroke-opacity=".7"/>'
            f'<path d="M{lw} 0 V{h}" stroke="{color}" stroke-opacity=".5"/><path d="{clipped_corners(lw, 0, rw, h, 7)}" fill="{color}" fill-opacity=".16"/>'
            + ts.text(left, 12, 21, size, C["ivory"], tracking=0.5, opacity=0.85)
            + ts.text(right, lw + 12, 21, size, color, tracking=0.5, bold=0.25)
            + "</g>"
        )
        x += lw + rw + gap
    width = int(x - gap) + 2
    return svg_doc(width, 40, "".join(parts), ts.defs(), "Chiffres du projet", "Écussons : nanos world en Lua 5.4, Unreal 5.7, 8 voies, 176 lames, 63 effets Niagara, 6 suites de tests de simulation, 61 issues, projet de fan sans lien officiel."), width
