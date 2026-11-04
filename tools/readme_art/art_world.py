"""Images qui racontent le jeu : séparateurs de chapitre, les deux camps, les huit voies, le parcours d'une partie."""
import math

import data
from art_banner import moon, sky_defs, sun
from glyphs import Typeset
from parts import STATUS, chip, diamond, fmt, gauge, plate, seal
from theme import C, clipped_corners, grad, ink_filter, patterns, radial, svg_doc

CHAPTERS = [
    ("壱", "LE JEU", "序"),
    ("弐", "DEUX CAMPS", "対"),
    ("参", "LES HUIT VOIES", "呼"),
    ("肆", "LE DÉMON", "鬼"),
    ("伍", "UNE PARTIE", "道"),
    ("陸", "SOUS LE CAPOT", "構"),
    ("漆", "LES ASSETS", "匠"),
    ("捌", "DÉMARRER", "始"),
    ("玖", "FEUILLE DE ROUTE", "暦"),
    ("拾", "DIRECTION ARTISTIQUE", "彩"),
    ("拾壱", "CONTRIBUER", "結"),
]


def chapter(index):
    """Bandeau de chapitre : sceau numéroté, étiquette, lame, kanji fantôme. Le titre lisible est le titre Markdown qui suit."""
    numeral, label, ghost = CHAPTERS[index]
    ts = Typeset()
    W, H = 1000, 84
    defs = (
        grad("line", [(0, C["blood"], 1), (0.7, C["blood"], 0.35), (1, C["blood"], 0)], 0, 0, 1, 0)
        + radial("sealG", [(0, "#C02040", None), (1, "#6A0C18", None)], 0.35, 0.3, 0.8)
        + ink_filter()
    )
    num_size = 30 if len(numeral) == 1 else 21
    body = [
        f'<path d="{clipped_corners(1, 1, W - 2, H - 2, 12)}" fill="#0C0609" stroke="{C["blood"]}" stroke-opacity=".35"/>',
        ts.text(ghost, 940, 76, 96, C["ivory"], anchor="middle", opacity=0.07, extra='filter="url(#ink)"'),
        f'<path d="M78 46 H900" stroke="url(#line)" stroke-width="2"/>',
        f'<path d="M78 46 H118" stroke="{C["blood"]}" stroke-width="2.5"/>',
        f'<path d="M900 46 l36 -6 l-8 6 l8 6Z" fill="{C["blood"]}" opacity=".5"/>',
        f'<g class="hb"><path d="M42 8 L78 44 L42 80 L6 44Z" fill="url(#sealG)" stroke="{C["bright"]}" stroke-opacity=".7" stroke-width="1.5"/></g>',
        ts.text(numeral, 42, 44 + num_size * 0.36, num_size, C["ivory"], anchor="middle", bold=0.5),
        ts.text(f"CHAPITRE {index + 1}", 96, 36, 12, C["bright"], tracking=4, bold=0.2),
        ts.text(label, 96, 70, 17, C["ivory"], tracking=5, opacity=0.9, bold=0.3),
    ]
    return svg_doc(W, H, "".join(body), defs + ts.defs(), f"Chapitre {index + 1} : {label.capitalize()}", f"Séparateur de chapitre : {label.lower()}.")


def _bullets(ts, items, x, y, width, color, size=15, gap=11, marker_color=None):
    """Liste à puces en losange. Renvoie (markup, y suivant)."""
    out = []
    for text in items:
        lines, h = ts.lines(text, x + 20, y, size, width - 20, leading=1.38, fill=C["ivory"], opacity=0.92)
        out.append(diamond(x + 5, y - size * 0.32, 4, marker_color or color) + lines)
        y += h + gap
    return "".join(out), y


def camps():
    ts = Typeset()
    W, H = 1000, 520
    slayers = [k for k in data.ORDER if k != "Demon"]
    hp_min = min(data.CLASSES[k]["hp"] for k in slayers)
    hp_max = max(data.CLASSES[k]["hp"] for k in slayers)
    low = min(slayers, key=lambda k: data.CLASSES[k]["hp"])
    high = max(slayers, key=lambda k: data.CLASSES[k]["hp"])
    demon = data.CLASSES["Demon"]
    tiers = data.DEMON["tiers"]
    n_slayer, n_demon = len(data.RANKS["slayer"]), len(data.RANKS["demon"])
    defs = (
        sky_defs() + patterns() + ink_filter()
        + grad("slayerBg", [(0, "#0A2234", None), (1, "#050B12", None)]) + grad("demonBg", [(0, "#2A0B14", None), (1, "#0D0407", None)])
        + '<linearGradient id="fadeTop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".9"/></linearGradient>'
        + '<mask id="fadeLow" maskUnits="userSpaceOnUse" x="0" y="360" width="1000" height="160"><rect x="0" y="360" width="1000" height="160" fill="url(#fadeTop)"/></mask>'
    )
    px, py, pw, ph = 8, 8, 470, 504
    qx = 1000 - 8 - pw
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>']

    # --- pourfendeur
    body.append(plate(px, py, pw, ph, "url(#slayerBg)", C["slayer"], cut=18))
    body.append(f'<g mask="url(#fadeLow)" opacity=".5"><rect x="{px + 2}" y="400" width="{pw - 4}" height="106" fill="url(#seigaiha)"/></g>')
    body.append(ts.text("鬼殺", px + 26, py + 100, 74, C["slayer"], bold=1.2, extra='filter="url(#ink)"'))
    body.append(ts.text("POURFENDEUR", px + 26, py + 146, 27, C["ivory"], tracking=5, bold=0.5))
    body.append(ts.text("Un souffle, une lame Nichirin, la nuit à tenir jusqu'à l'aube.", px + 26, py + 176, 15, C["ice"]))
    body.append(sun(px + 392, py + 84, 26))
    items = [
        f"7 souffles : Eau, Foudre, Flamme, Vent, Brume, Pierre, Insecte, avec 4 techniques chacun et des délais de recharge",
        f"{data.WEAPONS} lames Nichirin à forger, équiper et faire briller grâce à des traînées d'effets",
        f"{n_slayer} grades, du Mizunoto au Hashira, qui donnent des PV",
        f"De {fmt(hp_min)} PV (souffle de l'{low}) à {fmt(hp_max)} PV (souffle de la {high}) selon la voie",
    ]
    bullets, y_end = _bullets(ts, items, px + 28, py + 226, pw - 56, C["slayer"])
    body.append(bullets)
    for i, key in enumerate(slayers):
        cls = data.CLASSES[key]
        body.append(seal(ts, px + 46 + i * 62, py + ph - 46, 22, cls["glyph"], cls["color"], size=24))

    # --- démon
    body.append(plate(qx, py, pw, ph, "url(#demonBg)", C["blood"], cut=18))
    body.append(f'<g mask="url(#fadeLow)" opacity=".55"><rect x="{qx + 2}" y="400" width="{pw - 4}" height="106" fill="url(#scale-blood)"/></g>')
    body.append(ts.text("鬼", qx + 26, py + 100, 74, C["blood"], bold=1.2, extra='filter="url(#ink)"'))
    body.append(ts.text("DÉMON", qx + 26, py + 146, 27, C["ivory"], tracking=5, bold=0.5))
    body.append(ts.text("La nuit t'appartient : ta chair se recoud, ton sang frappe.", qx + 26, py + 176, 15, C["bright"]))
    body.append(moon(qx + 392, py + 84, 30))
    for k in range(3):
        x0 = qx + 372 + k * 18
        body.append(f'<line x1="{x0}" y1="{py + 40}" x2="{x0 - 26}" y2="{py + 130}" stroke="#FFD2D6" stroke-width="2.4" stroke-linecap="round" opacity=".8"/>')
    regen = data.DEMON["regen"]["base"] * 100
    items = [
        f"Le sang paie les techniques : {fmt(data.DEMON['blood']['max'])} au maximum, {fmt(data.DEMON['blood']['perSecond'])} de plus chaque seconde",
        f"Régénération passive de {fmt(round(regen, 1))} % des PV par seconde après {data.DEMON['combatSeconds']} s sans combat",
        f"Dévorer cadavres et civils : de la chair, des âmes, {len(tiers)} paliers de puissance",
        f"{n_demon} grades, du Démon errant à la Lune Supérieure Une ; {fmt(demon['hp'])} PV et aucune arme",
    ]
    bullets, _ = _bullets(ts, items, qx + 28, py + 226, pw - 56, C["blood"])
    body.append(bullets)
    gx = qx + 28
    for i, (label, value, color) in enumerate((("SANG", 0.62, C["blood"]), ("CHAIR", 0.55, C["flesh"]), ("ÂMES", 0.73, C["soul"]))):
        x0 = gx + i * 140
        body.append(ts.text(label, x0, py + ph - 56, 11, C["ivory"], tracking=2, opacity=0.8))
        body.append(gauge(x0, py + ph - 46, 120, 9, value, color, delay=0.2 * i))

    # --- au centre : la lame et « contre »
    body.append(f'<line x1="520" y1="-10" x2="478" y2="530" stroke="{C["ivory"]}" stroke-width="2" opacity=".6"/>')
    body.append(diamond(500, 262, 30, "#12070B", C["ivory"], 0.9))
    body.append(ts.text("対", 500, 274, 30, C["ivory"], anchor="middle", bold=0.5))
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "Les deux camps",
                   "Pourfendeurs : 7 souffles, des lames Nichirin, 11 grades. Démons : sang, régénération, dévoration, 5 paliers de puissance, 8 grades.")


def _radar(cx, cy, r, values, color):
    """Radar à quatre axes : dégâts en haut, survie à droite, soutien en bas, contrôle à gauche."""
    axes = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    grid = "".join(
        f'<path d="M{cx} {cy - r * k} L{cx + r * k} {cy} L{cx} {cy + r * k} L{cx - r * k} {cy} Z" fill="none" stroke="#EFE3D0" stroke-opacity="{0.16 if k < 1 else 0.3}"/>' for k in (0.33, 0.66, 1.0)
    )
    cross = f'<path d="M{cx} {cy - r} V{cy + r} M{cx - r} {cy} H{cx + r}" stroke="#EFE3D0" stroke-opacity=".18"/>'
    pts = " ".join(f"{cx + ax * r * v / 100:.1f},{cy + ay * r * v / 100:.1f}" for (ax, ay), v in zip(axes, values))
    return grid + cross + f'<polygon points="{pts}" fill="{color}" fill-opacity=".32" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>' + "".join(
        f'<circle cx="{cx + ax * r * v / 100:.1f}" cy="{cy + ay * r * v / 100:.1f}" r="3" fill="{color}"/>' for (ax, ay), v in zip(axes, values)
    )


def breaths():
    ts = Typeset()
    cw, ch, gap = 229, 304, 28
    W = 4 * cw + 3 * gap
    H = 2 * ch + gap + 52
    defs = ink_filter()
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>']
    for i, key in enumerate(data.ORDER):
        cls = data.CLASSES[key]
        col, row = i % 4, i // 4
        x, y = col * (cw + gap), row * (ch + gap)
        color = cls["color"]
        body.append(plate(x, y, cw, ch, "#0E0709", color, cut=14, stroke_opacity=0.55))
        body.append(f'<path d="M{x + 14} {y} H{x + cw - 14}" stroke="{color}" stroke-width="3" opacity=".9"/>')
        body.append(seal(ts, x + 40, y + 46, 26, cls["glyph"], color, size=30, bold=0.8))
        name = cls["name"] if key != "Demon" else "Démon"
        body.append(ts.text(name.replace("Souffle ", "Souffle "), x + 78, y + 42, 14.5, C["ivory"], bold=0.3))
        body.append(ts.text(cls["short"], x + 78, y + 62, 11.5, color, opacity=0.95))
        cx, cy, r = x + cw / 2, y + 138, 44
        g = cls["gameplay"]
        body.append(_radar(cx, cy, r, [g["damage"], g["survival"], g["support"], g["control"]], color))
        for label, (dx, dy) in (("DÉGÂTS", (0, -r - 8)), ("SURVIE", (r + 8, 4)), ("SOUTIEN", (0, r + 17)), ("CONTRÔLE", (-r - 8, 4))):
            anchor = "middle" if dx == 0 else ("start" if dx > 0 else "end")
            body.append(ts.text(label, cx + dx, cy + dy, 8.5, C["ivory"], anchor=anchor, tracking=1, opacity=0.55))
        body.append(ts.text(f"{fmt(cls['hp'])} PV", x + 16, y + 214, 15, color, bold=0.3))
        body.append(ts.text("4 techniques", x + cw - 16, y + 214, 11.5, C["ivory"], anchor="end", opacity=0.55, tracking=1))
        for j, spell in enumerate(cls["spells"]):
            sy = y + 238 + j * 17
            body.append(ts.text(str(j + 1), x + 16, sy, 11, color, bold=0.3))
            body.append(ts.text(spell["name"], x + 32, sy, 12, C["ivory"], opacity=0.9))
    ly = 2 * ch + gap + 28
    body.append(ts.text("Profil de chaque voie : dégâts, survie, soutien et contrôle, de 0 à 100 (Shared/Classes.lua).", W / 2, ly, 12.5, C["ivory"], anchor="middle", opacity=0.6, tracking=0.3))
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "Les huit voies",
                   "Huit cartes : Eau, Foudre, Flamme, Vent, Brume, Pierre, Insecte et Démon, avec leur kanji, leurs points de vie, leur profil en radar et leurs quatre techniques.")


JOURNEY = [
    ("壱", "Arrivée", "choix du camp, une fois par personnage", "en cours", "A12"),
    ("弐", "Premier tirage", "un souffle ou un pouvoir sanguinaire, au sort", "à faire", "A13 A14 A15"),
    ("参", "Progression", "grades, quêtes, chasse, compétences", "à faire", "A6 A7 A17"),
    ("肆", "Combat", "techniques, sabre, parade, soleil, glycine", "en cours", "A4 A22 A21 A25"),
    ("伍", "Puissance du démon", "sang, chair, âmes, repas par jour", "en cours", "A5 A18"),
    ("陸", "Économie", "yens, forge, craft, équipement, boutique", "à faire", "A26 A28 B7 B14"),
    ("漆", "Monde", "maisons, coffres, récolte, carte", "à faire", "A19 A20 B19 B6"),
]


def journey():
    ts = Typeset()
    W, H = 1000, 430
    n = len(JOURNEY)
    xs = [78 + i * (W - 156) / (n - 1) for i in range(n)]
    ys = [158 if i % 2 == 0 else 274 for i in range(n)]
    path = f"M{xs[0]} {ys[0]}"
    for i in range(1, n):
        dx = (xs[i] - xs[i - 1]) / 2
        path += f" C{xs[i - 1] + dx:.1f} {ys[i - 1]} {xs[i] - dx:.1f} {ys[i]} {xs[i]:.1f} {ys[i]}"
    road = (
        f'<linearGradient id="roadG" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0">'
        f'<stop offset="0" stop-color="{C["slayer"]}"/><stop offset=".5" stop-color="{C["ivory"]}"/><stop offset="1" stop-color="{C["blood"]}"/></linearGradient>'
    )
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>',
            f'<path d="{path}" fill="none" stroke="#2A1018" stroke-width="12" stroke-linecap="round"/>',
            f'<path d="{path}" fill="none" stroke="url(#roadG)" stroke-width="3" stroke-linecap="round" stroke-dasharray="4 10" class="dsh" opacity=".9"/>']
    for i, (numeral, title, sub, status, _tasks) in enumerate(JOURNEY):
        x, y = xs[i], ys[i]
        label, color = STATUS[status]
        up = i % 2 == 0
        body.append(f'<circle cx="{x}" cy="{y}" r="36" fill="{color}" opacity=".13" class="glw"/>')
        body.append(seal(ts, x, y, 27, numeral, color, size=26, fill="#0E0709", bold=0.5, ring=2.4))
        if up:  # le bloc de texte est au-dessus du sceau : titre, description, puis l'état
            title_y, sub_y, chip_y = 36, 58, y - 27 - 11 - 20
        else:  # en dessous : l'état, puis le titre et la description
            chip_y, title_y, sub_y = y + 27 + 11, y + 27 + 11 + 20 + 26, y + 27 + 11 + 20 + 48
        body.append(ts.text(title, x, title_y, 15.5, C["ivory"], anchor="middle", bold=0.35))
        body.append(ts.lines(sub, x, sub_y, 11.5, 130, leading=1.32, fill=C["ivory"], anchor="middle", opacity=0.72)[0])
        body.append(chip(ts, x, chip_y, label, color, size=10, h=20, tracking=1, anchor="middle")[0])
    return svg_doc(W, H, "".join(body), road + ts.defs(), "Le parcours du joueur",
                   "Sept étapes : arrivée, premier tirage, progression, combat, puissance du démon, économie, monde, avec l'état de chacune.")
