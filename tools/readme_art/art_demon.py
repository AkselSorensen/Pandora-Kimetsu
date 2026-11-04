"""Images du camp démon : paliers, repas, sang, la boucle, la dévoration."""
import math

import data
from art_banner import moon
from glyphs import Typeset
from parts import arrow, chip, diamond, fmt, gauge, plate, seal
from theme import C, grad, ink_filter, radial, svg_doc


def _title(ts, x, y, text, ghost, color=None):
    return ts.text(text, x, y, 12.5, color or C["bright"], tracking=3.5, bold=0.25) + ts.text(ghost, x + ts.width(text, 12.5, 3.5) + 14, y + 1, 15, C["ivory"], opacity=0.25)


def stats():
    ts = Typeset()
    W, H = 1000, 660
    d = data.DEMON
    tiers = d["tiers"]
    ranks = data.RANKS["demon"]
    perRank = d["meals"]["perRank"]
    costs = d["blood"]["costs"]
    spells = data.CLASSES["Demon"]["spells"]
    rate = d["blood"]["perSecond"]
    defs = (
        grad("soulG", [(0, "#5A2A9A", None), (1, "#B06FE0", None)]) + grad("bloodG", [(0, "#8A0F1C", None), (1, "#FF6A74", None)]) + grad("goldG", [(0, "#8A6A08", None), (1, "#F2C20F", None)])
        + ink_filter()
    )
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>']

    # --- A : paliers de puissance
    ax, ay, aw, ah = 8, 8, 570, 330
    body.append(plate(ax, ay, aw, ah, "#0D0709", C["blood"], cut=14, stroke_opacity=0.45))
    body.append(_title(ts, ax + 22, ay + 30, "PALIERS DE PUISSANCE", "段"))
    body.append(ts.text("selon les âmes dévorées", ax + aw - 22, ay + 30, 12, C["ivory"], anchor="end", opacity=0.55))
    base = ay + ah - 98
    colw, gap = 84, 26
    left = ax + 28
    max_hp = max(t["hp"] for t in tiers)
    for i, t in enumerate(tiers):
        x = left + i * (colw + gap)
        h = 14 + (t["hp"] / max_hp) * 150
        body.append(f'<rect x="{x}" y="{base - h:.1f}" width="{colw}" height="{h:.1f}" rx="4" fill="url(#soulG)" opacity="{0.45 + 0.1 * i:.2f}" class="col" style="animation-delay:{0.12 * i:.2f}s"/>')
        body.append(f'<path d="M{x} {base - h:.1f} H{x + colw}" stroke="#E6C8FF" stroke-width="2"/>')
        body.append(ts.text("+" + fmt(t["hp"]) + " PV" if t["hp"] else "aucun bonus", x + colw / 2, base - h - 30, 13, C["ivory"], anchor="middle", bold=0.3))
        extra = f"+{fmt(t['damagePct'])} % dégâts" if t["damagePct"] else "—"
        body.append(ts.text(extra, x + colw / 2, base - h - 12, 11, C["flesh"], anchor="middle"))
        body.append(f'<circle cx="{x + colw / 2}" cy="{base + 16}" r="10" fill="#1B0A0F" stroke="{C["soul"]}" stroke-width="1.5"/>')
        body.append(ts.text(str(i + 1), x + colw / 2, base + 20.5, 12, C["ivory"], anchor="middle", bold=0.3))
        for j, line in enumerate(ts.wrap(t["name"], 11.5, colw + 14)):
            body.append(ts.text(line, x + colw / 2, base + 44 + j * 14, 11.5, C["ivory"], anchor="middle", opacity=0.9))
        body.append(ts.text(f"{t['souls']} âmes" if t["souls"] else "départ", x + colw / 2, base + 76, 11, C["soul"], anchor="middle", bold=0.2))
    unlock = d["unlock"]["4"]
    ux = left + (unlock - 1) * (colw + gap)
    body.append(f'<path d="M{ux + colw / 2} {ay + 54} v14" stroke="{C["gold"]}" stroke-width="1.5"/>')
    body.append(chip(ts, ux + colw / 2, ay + 38, "TECHNIQUE 4", C["gold"], size=10, h=18, tracking=1.2, anchor="middle")[0])
    body.append(ts.text(f"Faim : {d['souls']['hungerSeconds']} s sans repas font perdre un palier.", ax + 22, ay + ah - 10, 12, C["ivory"], opacity=0.6))

    # --- B : repas par jour
    bx, bw = 594, 398
    body.append(plate(bx, ay, bw, ah, "#0D0709", C["gold"], cut=14, stroke_opacity=0.4))
    body.append(_title(ts, bx + 22, ay + 30, "REPAS PAR JOUR", "食", C["gold"]))
    n = len(ranks)
    cw = (bw - 44 - (n - 1) * 8) / n
    caps = [perRank * (i + 1) for i in range(n)]
    top = max(caps)
    for i, r in enumerate(ranks):
        x = bx + 22 + i * (cw + 8)
        h = 10 + caps[i] / top * 168
        body.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{cw:.1f}" height="{h:.1f}" rx="3" fill="url(#goldG)" class="col" style="animation-delay:{0.1 * i:.2f}s" opacity=".92"/>')
        body.append(ts.text(str(caps[i]), x + cw / 2, base - h - 8, 14, C["gold"], anchor="middle", bold=0.3))
        body.append(ts.text(r["kanji"], x + cw / 2, base + 24, 15 if len(r["kanji"]) == 1 else 13, C["ivory"], anchor="middle", opacity=0.9))
        body.append(ts.text(str(i + 1), x + cw / 2, base + 44, 11, C["ivory"], anchor="middle", opacity=0.45))
    body.append(ts.text(f"{perRank} repas de plus à chaque grade (du 1 au {n}) · un jour dure {d['meals']['dayLength'] // 3600} h", bx + 22, ay + ah - 14, 12, C["ivory"], opacity=0.6))

    # --- C : le sang
    cy0 = 354
    body.append(plate(8, cy0, 984, 296, "#0D0709", C["blood"], cut=14, stroke_opacity=0.45))
    body.append(_title(ts, 30, cy0 + 32, "LE SANG PAIE LES TECHNIQUES", "血"))
    body.append(ts.text(f"réserve de {d['blood']['max']}, qui se refait de {fmt(rate)} par seconde", 970, cy0 + 32, 12, C["ivory"], anchor="end", opacity=0.55))
    track_x, track_w = 330, 400
    for i, cost in enumerate(costs):
        y = cy0 + 62 + i * 54
        spell = spells[i]
        locked = i + 1 == 4
        body.append(seal(ts, 52, y + 18, 20, spell.get("glyph", "鬼"), C["blood"], size=22, bold=0.6))
        body.append(ts.text(spell["name"], 86, y + 14, 14.5, C["ivory"], bold=0.3))
        body.append(ts.text(f"technique {i + 1}" + (f" · verrouillée jusqu'au palier {d['unlock']['4']}" if locked else ""), 86, y + 33, 11.5, C["gold"] if locked else C["ivory"], opacity=0.8 if locked else 0.5))
        body.append(f'<rect x="{track_x}" y="{y + 6}" width="{track_w}" height="22" rx="4" fill="#1B0A0F" stroke="#E0344B" stroke-opacity=".25"/>')
        body.append(f'<rect x="{track_x}" y="{y + 6}" width="{track_w * cost / d["blood"]["max"]:.1f}" height="22" rx="4" fill="url(#bloodG)" class="bar" style="animation-delay:{0.15 * i:.2f}s"/>')
        body.append(ts.text(f"{cost} de sang", track_x + track_w * cost / d["blood"]["max"] + 10, y + 22, 13, C["bright"], bold=0.3))
        body.append(ts.text(f"{fmt(round(cost / rate, 1))} s", 970, y + 24, 22, C["ivory"], anchor="end", bold=0.4))
        body.append(ts.text("pour le regagner", 970, y + 40, 10.5, C["ivory"], anchor="end", opacity=0.5))
    body.append(ts.text("Les quatre ensemble : " + fmt(sum(costs)) + " de sang, soit " + fmt(round(sum(costs) / rate)) + " s de réserve.", 30, cy0 + 280, 12, C["ivory"], opacity=0.6))
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "Le système du démon en chiffres",
                   "Trois graphiques tirés du code : les 5 paliers de puissance selon les âmes, les repas par jour selon le grade, et le coût en sang de chaque technique avec le temps pour le regagner.")


LOOP = [
    ("狩", "Chasser", "un cadavre de joueur ou un civil du Domaine"),
    ("食", "Dévorer", "touche H, accroupi pendant 3,5 s"),
    ("得", "Gagner", "chair, âmes, PV et XP"),
    ("昇", "Monter", "5 paliers : PV, dégâts, régénération"),
    ("闘", "Se battre", "le sang paie les techniques"),
    ("飢", "Avoir faim", "240 s sans repas : un palier perdu"),
]


def loop():
    ts = Typeset()
    W, H = 1000, 490
    cx, cy, rx, ry = 500, 238, 318, 146
    defs = radial("coreG", [(0, C["blood"], 0.35), (1, C["blood"], 0)]) + ink_filter()
    ring = f"M{cx - rx} {cy} A{rx} {ry} 0 1 1 {cx + rx} {cy} A{rx} {ry} 0 1 1 {cx - rx} {cy} Z"
    # le sens de parcours : en haut à gauche vers la droite (horaire) ; on part du haut
    start = f"M{cx} {cy - ry} A{rx} {ry} 0 1 1 {cx} {cy + ry} A{rx} {ry} 0 1 1 {cx} {cy - ry} Z"
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>', f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + 90}" ry="{ry + 90}" fill="url(#coreG)"/>']
    body.append(ts.text("鬼", cx, cy + 50, 170, C["ivory"], anchor="middle", opacity=0.07, extra='filter="url(#ink)"'))
    body.append(f'<path d="{ring}" fill="none" stroke="#2A1018" stroke-width="14"/>')
    body.append(f'<path d="{ring}" fill="none" stroke="{C["blood"]}" stroke-width="2.5" stroke-dasharray="4 9" class="dsh" opacity=".9"/>')
    n = len(LOOP)
    for i in range(n):
        th = -math.pi / 2 + (i + 0.5) * math.tau / n
        px, py = cx + rx * math.cos(th), cy + ry * math.sin(th)
        ang = math.atan2(ry * math.cos(th), -rx * math.sin(th))
        pts = [(px + 11 * math.cos(ang), py + 11 * math.sin(ang)), (px + 8 * math.cos(ang + 2.5), py + 8 * math.sin(ang + 2.5)), (px + 8 * math.cos(ang - 2.5), py + 8 * math.sin(ang - 2.5))]
        body.append('<path d="M' + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + f'Z" fill="{C["bright"]}"/>')
    for i, (glyph, title, sub) in enumerate(LOOP):
        th = -math.pi / 2 + i * math.tau / n
        px, py = cx + rx * math.cos(th), cy + ry * math.sin(th)
        hunger = glyph == "飢"
        color = C["gold"] if hunger else C["blood"]
        body.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="40" fill="{color}" opacity=".12" class="glw"/>')
        body.append(seal(ts, px, py, 30, glyph, color, size=32, fill="#12070B", bold=0.7, ring=2.6))
        if abs(math.cos(th)) < 0.2:  # haut et bas : le texte passe au-dessus ou en dessous du sceau
            title_y, sub_y = (py - 64, py - 45) if math.sin(th) < 0 else (py + 68, py + 87)
            body.append(ts.text(title, px, title_y, 17, C["ivory"], anchor="middle", bold=0.4))
            body.append(ts.text(sub, px, sub_y, 12, C["ivory"], anchor="middle", opacity=0.7))
        else:
            right = math.cos(th) > 0
            tx = px + 50 if right else px - 50
            anchor = "start" if right else "end"
            body.append(ts.text(title, tx, py - 2, 17, C["ivory"], anchor=anchor, bold=0.4))
            lines, _ = ts.lines(sub, tx, py + 18, 12, 150, leading=1.3, fill=C["ivory"], anchor=anchor, opacity=0.7)
            body.append(lines)
    # points qui parcourent la boucle
    for k, dur in enumerate((14, 14)):
        body.append(f'<circle r="5.5" fill="#fff"><animateMotion dur="{dur}s" repeatCount="indefinite" begin="-{k * dur / 2}s" path="{start}"/></circle>')
        body.append(f'<circle r="11" fill="{C["bright"]}" opacity=".35"><animateMotion dur="{dur}s" repeatCount="indefinite" begin="-{k * dur / 2}s" path="{start}"/></circle>')
    body.append(ts.text("LA BOUCLE DU DÉMON", cx, cy - 4, 16, C["bright"], anchor="middle", tracking=5, bold=0.3))
    body.append(ts.text("sans repas, la puissance retombe", cx, cy + 20, 12.5, C["ivory"], anchor="middle", opacity=0.6))
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "La boucle du démon",
                   "Six étapes qui se répètent : chasser, dévorer, gagner, monter, se battre, avoir faim.")


def devour():
    ts = Typeset()
    W, H = 1000, 360
    src = data.DEMON["sources"]
    dv = data.DEMON["devour"]
    defs = grad("meal", [(0, "#8A0F1C", None), (1, "#FF6A74", None)], 0, 0, 1, 0)
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>']
    y0, bh = 28, 200

    def box(x, w, title, color=C["blood"]):
        return plate(x, y0, w, bh, "#0D0709", color, cut=12, stroke_opacity=0.6) + ts.text(title, x + 16, y0 + 28, 12, color, tracking=2.5, bold=0.25)

    # 1 : la touche
    body.append(box(10, 170, "1 · LA TOUCHE"))
    body.append(plate(62, y0 + 56, 66, 58, "#1B0A0F", C["ivory"], cut=8, stroke_opacity=0.9, width=2))
    body.append(ts.text(data.DEMON["devourKey"], 95, y0 + 98, 34, C["ivory"], anchor="middle", bold=0.6))
    body.append(ts.lines("près d'une proie, quand on est démon", 95, y0 + 144, 12.5, 142, leading=1.35, fill=C["ivory"], anchor="middle", opacity=0.8)[0])
    # 2 : les conditions
    body.append(box(214, 250, "2 · LE SERVEUR VÉRIFIE"))
    checks = [f"le camp est démon", f"la proie est à moins de {dv['range']} cm", "il reste un repas pour aujourd'hui", "la proie n'a jamais été mangée"]
    for i, text in enumerate(checks):
        yy = y0 + 62 + i * 33
        body.append(f'<path d="M{232} {yy - 4} l5 6 l10 -12" fill="none" stroke="{C["jade"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')
        body.append(ts.text(text, 256, yy + 2, 13, C["ivory"], opacity=0.92))
    # 3 : le geste
    body.append(box(508, 250, "3 · LE GESTE"))
    body.append(ts.text(f"accroupi {fmt(dv['seconds'])} s", 633, y0 + 82, 22, C["ivory"], anchor="middle", bold=0.4))
    body.append(f'<rect x="530" y="{y0 + 104}" width="206" height="14" rx="7" fill="#1B0A0F" stroke="#E0344B" stroke-opacity=".4"/>')
    body.append(f'<rect x="530" y="{y0 + 104}" width="206" height="14" rx="7" fill="url(#meal)" class="bar" style="animation-duration:3.5s;animation-iteration-count:infinite"/>')
    body.append(ts.lines("Le HUD montre la barre, le temps restant et le gain attendu.", 633, y0 + 146, 12, 220, leading=1.35, fill=C["ivory"], anchor="middle", opacity=0.7)[0])
    # 4 : les gains
    body.append(box(802, 188, "4 · LES GAINS", C["gold"]))
    for i, (label, key) in enumerate((("Cadavre d'un joueur", "corpse"), ("Civil du Domaine", "civil"))):
        s = src[key]
        yy = y0 + 62 + i * 66
        body.append(ts.text(label, 820, yy, 13, C["ivory"], bold=0.3))
        body.append(ts.text(f"+{s['flesh']} chair · +{s['souls']} âmes", 820, yy + 19, 12, C["flesh"]))
        body.append(ts.text(f"+{int(round(s['heal'] * 100))} % PV · +{s['xp']} XP", 820, yy + 35, 12, C["soul"]))
    body.append(arrow(180, y0 + 100, 212, y0 + 100, C["bright"]))
    body.append(arrow(464, y0 + 100, 506, y0 + 100, C["bright"]))
    body.append(arrow(758, y0 + 100, 800, y0 + 100, C["gold"]))
    # l'échec : tout s'arrête sans rien consommer
    fy = y0 + bh + 34
    body.append(f'<path d="M633 {y0 + bh} V{fy - 6}" stroke="{C["blood"]}" stroke-width="2" stroke-dasharray="4 5" class="dsh"/>')
    body.append(plate(214, fy, 776, 62, "#1B0A0F", C["blood"], cut=10, stroke_opacity=0.8))
    body.append(ts.text("INTERROMPU : RIEN N'EST CONSOMMÉ", 234, fy + 24, 12, C["bright"], tracking=2.5, bold=0.3))
    body.append(ts.text(f"un coup reçu · une technique lancée · un pas de trop (plus de 330 cm) · la mort · la proie qui disparaît", 234, fy + 46, 12.5, C["ivory"], opacity=0.85))
    body.append(ts.text("Jamais un joueur vivant n'est une proie : seuls les corps déjà morts le sont, et la victime n'est pas touchée.", 10, H - 12, 12, C["ivory"], opacity=0.55))
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "Comment un démon dévore",
                   "La touche H près d'une proie, les vérifications du serveur, le geste de 3,5 secondes, les gains ; en cas d'interruption rien n'est consommé.")
