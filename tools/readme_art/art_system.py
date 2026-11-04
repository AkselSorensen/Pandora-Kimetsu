"""Images techniques : architecture, pipeline des assets, calendrier, avancement."""
import data
from glyphs import Typeset
from parts import arrow, chip, diamond, fmt, plate, seal
from theme import C, grad, ink_filter, patterns, svg_doc


def _node(ts, x, y, w, h, title, lines, color, size=12, title_size=13, align="start", fill="#0D0709", cut=10):
    out = [plate(x, y, w, h, fill, color, cut=cut, stroke_opacity=0.65)]
    tx = x + 14 if align == "start" else x + w / 2
    out.append(ts.text(title, tx, y + 24, title_size, color, anchor=align, bold=0.3, tracking=0.6))
    yy = y + 44
    for line in lines:
        got, hh = ts.lines(line, tx, yy, size, w - 28, leading=1.32, fill=C["ivory"], anchor=align, opacity=0.82)
        out.append(got)
        yy += hh + 2
    return "".join(out)


def architecture():
    ts = Typeset()
    W, H = 1000, 700
    defs = grad("shareG", [(0, "#241006", None), (1, "#12070B", None)])
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>']
    # rangée du haut : d'où viennent les assets et les addons
    body.append(_node(ts, 20, 14, 250, 98, "UNREAL ENGINE 5.7", ["plugin Forge : modèles, animations, effets"], C["ice"]))
    body.append(arrow(270, 60, 330, 60, C["ice"]))
    body.append(ts.text("cuisson", 300, 50, 10.5, C["ice"], anchor="middle", opacity=0.8, tracking=1))
    body.append(_node(ts, 330, 14, 250, 98, "Assets/<pack>", ["un dossier par pack, jamais dans le dépôt", "exigés par Package.toml"], C["gold"]))
    body.append(_node(ts, 640, 14, 340, 98, "ADDONS FACULTATIFS", ["admin · menu de props · boutique · caisses · ODM · vitrine d'effets", "ils parlent au serveur par Wakfu:EquipWeapon et Wakfu:ResetCamp ; la partie propre n'en charge aucun"], C["soul"]))
    body.append(arrow(455, 106, 455, 168, C["gold"]))
    body.append(arrow(815, 106, 815, 168, C["soul"]))
    # le conteneur nanos world
    body.append(plate(10, 150, 980, 540, "#09050A", C["blood"], cut=18, stroke_opacity=0.5))
    body.append(ts.text("NANOS WORLD", 34, 180, 13, C["bright"], tracking=4, bold=0.3))
    body.append(ts.text("Packages/wakfu-rp : le mode de jeu (l'identifiant historique est gardé)", 34 + ts.width("NANOS WORLD", 13, 4) + 22, 180, 12.5, C["ivory"], opacity=0.6))
    # serveur et client
    body.append(_node(ts, 34, 206, 380, 190, "SERVEUR · Server/Index.lua", ["L'autorité : l'état de chaque joueur, le camp, les techniques, le démon, les cadavres, la forge, les quêtes.", "Il valide chaque demande : distance, coût, camp, limite."], C["blood"], title_size=14))
    body.append(_node(ts, 586, 206, 380, 190, "CLIENT · Client/Index.lua", ["Les touches et les écrans. Il n'envoie que des intentions et affiche ce que le serveur renvoie.", "VfxPlayer.lua joue les effets ; le HUD est une page web (Client/UI)."], C["slayer"], title_size=14))
    # flux
    body.append(arrow(584, 262, 416, 262, C["slayer"], width=2.4))
    body.append(ts.text("intentions", 500, 250, 12, C["slayer"], anchor="middle", bold=0.3, tracking=1))
    body.append(ts.text("castIndex · devour · chooseCamp", 500, 282, 10, C["ice"], anchor="middle", opacity=0.75))
    body.append(arrow(416, 340, 584, 340, C["blood"], width=2.4))
    body.append(ts.text("état", 500, 328, 12, C["bright"], anchor="middle", bold=0.3, tracking=1))
    body.append(ts.text("state · demon · fx · notice", 500, 360, 10, C["bright"], anchor="middle", opacity=0.75))
    body.append(ts.text("événements « wakfu:* »", 500, 384, 10, C["ivory"], anchor="middle", opacity=0.5, tracking=0.5))
    # shared
    body.append(arrow(224, 480, 224, 398, C["gold"], dashed=False))
    body.append(arrow(776, 480, 776, 398, C["gold"], dashed=False))
    body.append(plate(34, 418, 932, 120, "url(#shareG)", C["gold"], cut=12, stroke_opacity=0.6))
    body.append(ts.text("SHARED · chargé des deux côtés", 54, 446, 14, C["gold"], tracking=1, bold=0.3))
    body.append(ts.text("logique pure, sans appel au moteur : c'est ce qui permet de la tester", 330, 446, 12, C["ivory"], opacity=0.7))
    names = ["Config", "Classes", "Ranks", "Demon", "Combat", "Items", "Quests", "Npcs", "Economy", "VfxPlan"]
    cx, cy = 54, 462
    for name in names:
        w = ts.width(name + ".lua", 11.5, 0.3) + 16
        if cx + w > 944:
            cx, cy = 54, cy + 34
        body.append(plate(cx, cy, w, 26, "#1B0A0F", C["gold"], cut=5, stroke_opacity=0.45, width=1))
        body.append(ts.text(name + ".lua", cx + w / 2, cy + 18, 11.5, C["ivory"], anchor="middle", tracking=0.3, opacity=0.92))
        cx += w + 7
    body.append(ts.text("Config.lua porte tous les réglages : un chiffre d'équilibrage ne se cache jamais dans la logique.", 54, 528, 11, C["ivory"], opacity=0.5))
    # tests
    body.append(plate(34, 566, 932, 100, "#0B1410", C["jade"], cut=12, stroke_opacity=0.55))
    body.append(ts.text("TESTS DE SIMULATION · tests/simulation", 54, 594, 14, C["jade"], tracking=1, bold=0.3))
    body.append(ts.lines("Le Lua du serveur et du client tourne dans un faux moteur (module lupa) ; le HUD est rendu dans Edge. On vérifie le raisonnement du code, pas le moteur : un nom de fonction nanos faux ne se voit qu'en jeu.", 54, 618, 12.5, 880, leading=1.35, fill=C["ivory"], opacity=0.8)[0])
    body.append(arrow(500, 566, 500, 542, C["jade"], dashed=False))
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "Architecture du projet",
                   "Unreal et Forge produisent les assets cuits. Dans nanos world, le serveur autoritaire et le client échangent des événements wakfu:*, et partagent une logique pure testée par simulation.")


PIPE = [
    ("1", "Source", ["addon GMod", "pack Fab", "création originale"], C["ice"]),
    ("2", "glTF", ["tools/gmod2nanos", "convertit les modèles"], C["ice"]),
    ("3", "Unreal 5.7", ["tools/unreal_tools", "import des modèles et effets"], C["ice"]),
    ("4", "Cuisson", ["plugin Forge", "écrit Assets/<pack>"], C["gold"]),
    ("5", "Master", ["gmod2nanos.master", "garde tout, cuisson après cuisson"], C["gold"]),
    ("6", "Listes Lua", ["gen_vfx_assets.py", "gen_yufu_weapons.py"], C["soul"]),
    ("7", "Déclaration", ["assets_requirements", "dans Package.toml"], C["blood"]),
]


def pipeline():
    ts = Typeset()
    W, H = 1000, 250
    n = len(PIPE)
    bw, gap = 122, 21
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>', f'<path d="M20 52 H980" stroke="#2A1018" stroke-width="8" stroke-linecap="round"/>', f'<path d="M20 52 H980" stroke="{C["blood"]}" stroke-width="2" stroke-dasharray="4 9" class="dsh" opacity=".8"/>']
    for i, (num, title, lines, color) in enumerate(PIPE):
        x = 10 + i * (bw + gap)
        body.append(seal(ts, x + bw / 2, 52, 24, num, color, size=24, fill="#0E0709", bold=0.5, ring=2.2))
        body.append(plate(x, 92, bw, 130, "#0D0709", color, cut=10, stroke_opacity=0.6))
        body.append(ts.text(title, x + bw / 2, 118, 14, color, anchor="middle", bold=0.35))
        yy = 142
        for line in lines:
            got, hh = ts.lines(line, x + bw / 2, yy, 11.5, bw - 16, leading=1.3, fill=C["ivory"], anchor="middle", opacity=0.82)
            body.append(got)
            yy += hh + 3
    body.append(ts.text("Aucun asset extrait d'un jeu commercial : addons du Workshop, packs sous licence claire, créations originales.", W / 2, H - 8, 12, C["ivory"], anchor="middle", opacity=0.55))
    return svg_doc(W, H, "".join(body), ts.defs(), "Le pipeline des assets",
                   "Sept étapes : source, glTF, import Unreal, cuisson Forge, master cumulatif, listes Lua générées, déclaration dans Package.toml.")


WEEKS = [
    ("S1", ["A12 camp", "A14 pouvoirs", "A15 pitié"], ["B3 admin", "B4 assets", "B1 sauvegarde"]),
    ("S2", ["A13 tirage", "A3 lames", "A2 raccourcis", "A6 grades"], ["B1 fin", "B15 audit", "B14 resets", "B8 tests", "B9 robustesse", "B10 pipeline"]),
    ("S3", ["A22 combat", "A8 PNJ"], ["B5 addons", "B7 boutique", "B6 carte"]),
    ("S4", ["A4 techniques", "A16 touches", "A29 chat"], ["B6 fin", "B12 identité", "B18 modération"]),
    ("S5", ["A5 démon", "A21 soleil"], ["B16 maison", "B17 glycine", "B13 sauvegardes"]),
    ("S6", ["A18 âmes", "A7 chasse"], ["B19 récolte", "B11 armes"]),
    ("S7", ["A20 coffres", "A24 VIP", "A19 maisons"], ["B8 tests"]),
    ("S8", ["A17 arbre", "A23 créateur"], ["B20 launcher"]),
    ("S9", ["A25 glycine", "A26 paliers"], []),
    ("S10", ["A27 reroll"], []),
    ("S11", ["A28 craft"], []),
    ("+", ["A9 couleurs", "A10 icônes", "A11 textes"], []),
]


def roadmap():
    ts = Typeset()
    prio = {i["key"]: int(i["labels"][1][1]) for i in data.ISSUES["issues"] if i["labels"][1] in ("P0", "P1", "P2")}
    colors = {0: C["bright"], 1: C["gold"], 2: C["ice"]}
    label_w = 64
    n = len(WEEKS)
    cw = (1000 - 16 - label_w) / n
    top = 44
    row_a = 4 * 24 + 16
    row_b = 6 * 24 + 16
    H = top + row_a + row_b + 78
    W = 1000
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>']
    # colonnes et en-têtes
    for i, (week, _a, _b) in enumerate(WEEKS):
        x = 8 + label_w + i * cw
        if i % 2 == 0:
            body.append(f'<rect x="{x:.1f}" y="{top - 8}" width="{cw:.1f}" height="{row_a + row_b + 8}" fill="#120A0E"/>')
        body.append(ts.text(week, x + cw / 2, 26, 13, C["ivory"], anchor="middle", tracking=1, bold=0.3, opacity=0.85))
    lanes = [("DEV A", "jeu et interface", C["slayer"], top, row_a, 1), ("DEV B", "serveur et outils", C["jade"], top + row_a, row_b, 2)]
    for name, sub, color, y, h, which in lanes:
        body.append(f'<rect x="8" y="{y}" width="984" height="{h}" fill="none" stroke="{color}" stroke-opacity=".35"/>')
        body.append(f'<rect x="8" y="{y}" width="{label_w - 6}" height="{h}" fill="{color}" fill-opacity=".16"/>')
        body.append(ts.text(name, 8 + (label_w - 6) / 2, y + 26, 12.5, color, anchor="middle", bold=0.4, tracking=1))
        for line_no, word in enumerate(sub.split(" ")):
            body.append(ts.text(word, 8 + (label_w - 6) / 2, y + 44 + line_no * 12, 9.5, C["ivory"], anchor="middle", opacity=0.55))
        for i, week in enumerate(WEEKS):
            x = 8 + label_w + i * cw
            for j, task in enumerate(week[which]):
                key = task.split(" ")[0]
                color_task = colors[prio.get(key, 1)]
                size = 10.5
                while ts.width(task, size, 0) > cw - 12 and size > 8:
                    size -= 0.5
                ty = y + 8 + j * 24
                body.append(f'<rect x="{x + 3:.1f}" y="{ty}" width="{cw - 6:.1f}" height="20" rx="3" fill="{color_task}" fill-opacity=".15" stroke="{color_task}" stroke-opacity=".7"/>')
                body.append(ts.text(task, x + cw / 2, ty + 14, size, color_task, anchor="middle", bold=0.15))
    # légende
    ly = top + row_a + row_b + 36
    x = 8
    for label, color in (("P0 · à faire d'abord", colors[0]), ("P1 · jeu complet", colors[1]), ("P2 · finitions", colors[2])):
        body.append(f'<rect x="{x}" y="{ly - 12}" width="16" height="16" rx="3" fill="{color}" fill-opacity=".2" stroke="{color}"/>')
        body.append(ts.text(label, x + 24, ly + 1, 12.5, C["ivory"], opacity=0.85))
        x += 24 + ts.width(label, 12.5) + 30
    body.append(ts.text("Le calendrier suppose deux développeurs à plein temps ; il se décale si un seul avance.", 992, ly + 1, 11.5, C["ivory"], anchor="end", opacity=0.5))
    return svg_doc(W, H, "".join(body), ts.defs(), "Calendrier prévu sur onze semaines",
                   "Deux lignes, Dev A et Dev B, avec les tâches de chaque semaine, colorées selon leur priorité P0, P1 ou P2.")


def _donut(cx, cy, r, parts, width=22):
    import math

    total = sum(v for _, v, _ in parts)
    out, start = [], -math.pi / 2
    for label, v, color in parts:
        ang = v / total * math.tau
        x1, y1 = cx + r * math.cos(start), cy + r * math.sin(start)
        x2, y2 = cx + r * math.cos(start + ang - 0.04), cy + r * math.sin(start + ang - 0.04)
        large = 1 if ang > math.pi else 0
        out.append(f'<path d="M{x1:.1f} {y1:.1f} A{r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="butt"/>')
        start += ang
    return "".join(out)


def progress():
    ts = Typeset()
    issues = [i for i in data.ISSUES["issues"]]
    dev_a = [i for i in issues if "dev-a" in i["labels"]]
    dev_b = [i for i in issues if "dev-b" in i["labels"]]
    W, H = 1000, 470
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>']
    # carte 1 : répartition entre les deux développeurs
    body.append(plate(8, 8, 316, 214, "#0D0709", C["blood"], cut=12, stroke_opacity=0.45))
    body.append(ts.text("DEUX DÉVELOPPEURS", 26, 36, 12, C["bright"], tracking=3, bold=0.25))
    body.append(_donut(92, 136, 56, [("A", len(dev_a), C["slayer"]), ("B", len(dev_b), C["jade"])]))
    body.append(ts.text(str(len(issues)), 92, 146, 34, C["ivory"], anchor="middle", bold=0.6))
    body.append(ts.text("issues", 92, 166, 11, C["ivory"], anchor="middle", opacity=0.6, tracking=1))
    for k, (label, lst, color, sub) in enumerate((("Dev A", dev_a, C["slayer"], "jeu et interface"), ("Dev B", dev_b, C["jade"], "serveur, contenu, outils"))):
        y = 96 + k * 66
        body.append(ts.text(str(len(lst)), 176, y + 16, 34, color, bold=0.6))
        body.append(ts.text(label, 226, y - 2, 14, C["ivory"], bold=0.3))
        body.append(ts.text(sub, 226, y + 16, 11, C["ivory"], opacity=0.6))
    # carte 2 : priorités par développeur
    body.append(plate(338, 8, 316, 214, "#0D0709", C["gold"], cut=12, stroke_opacity=0.4))
    body.append(ts.text("PRIORITÉS", 356, 36, 12, C["gold"], tracking=3, bold=0.25))
    pcolors = {"P0": C["bright"], "P1": C["gold"], "P2": C["ice"]}
    for row, (label, lst, color) in enumerate((("Dev A", dev_a, C["slayer"]), ("Dev B", dev_b, C["jade"]))):
        y = 70 + row * 74
        body.append(ts.text(label, 356, y + 12, 13, color, bold=0.3))
        x = 356
        counts = {p: sum(1 for i in lst if p in i["labels"]) for p in ("P0", "P1", "P2")}
        total_w = 282
        for p in ("P0", "P1", "P2"):
            w = total_w * counts[p] / len(lst)
            body.append(f'<rect x="{x:.1f}" y="{y + 22}" width="{max(w - 3, 1):.1f}" height="26" rx="3" fill="{pcolors[p]}" fill-opacity=".85" class="bar" style="animation-delay:{0.1 * row}s"/>')
            body.append(ts.text(f"{p} · {counts[p]}", x + max(w - 3, 1) / 2, y + 40, 11.5, "#12070B", anchor="middle", bold=0.3))
            x += w
    # carte 3 : états
    body.append(plate(668, 8, 324, 214, "#0D0709", C["jade"], cut=12, stroke_opacity=0.4))
    body.append(ts.text("OÙ EN EST-ON", 686, 36, 12, C["jade"], tracking=3, bold=0.25))
    states = [
        ("fait", sum(1 for i in issues if i["state"] == "closed"), C["jade"]),
        ("en cours", sum(1 for i in issues if "en cours" in i["labels"]), C["gold"]),
        ("à vérifier en jeu", sum(1 for i in issues if "à vérifier en jeu" in i["labels"]), C["flesh"]),
    ]
    todo = len(issues) - sum(v for _, v, _ in states)
    states.append(("à faire", todo, "#9A8F86"))
    decisions = sum(1 for i in issues if "décision" in i["labels"])
    for k, (label, v, color) in enumerate(states):
        y = 66 + k * 28
        body.append(ts.text(str(v), 702, y + 10, 22, color, anchor="middle", bold=0.5))
        body.append(ts.text(label, 732, y + 8, 13, C["ivory"], opacity=0.88))
    body.append(ts.text(f"dont {decisions} décisions du projet à prendre", 686, 66 + 5 * 28 + 4, 11.5, C["soul"], opacity=0.9))
    # carte 4 : zones
    body.append(plate(8, 236, 984, 226, "#0D0709", C["blood"], cut=12, stroke_opacity=0.4))
    body.append(ts.text("PAR ZONE DU JEU", 26, 264, 12, C["bright"], tracking=3, bold=0.25))
    zones = {}
    for i in issues:
        for lab in i["labels"]:
            if lab.startswith("zone: "):
                zones[lab[6:]] = zones.get(lab[6:], 0) + 1
    ordered = sorted(zones.items(), key=lambda kv: -kv[1])
    mx = max(v for _, v in ordered)
    for k, (label, v) in enumerate(ordered):
        y = 284 + k * 24
        body.append(ts.text(label, 26, y + 13, 12.5, C["ivory"], opacity=0.88))
        w = 560 * v / mx
        body.append(f'<rect x="250" y="{y + 2}" width="{w:.1f}" height="14" rx="3" fill="url(#zoneG)" class="bar" style="animation-delay:{0.07 * k:.2f}s"/>')
        body.append(ts.text(str(v), 258 + w, y + 14, 12.5, C["bright"], bold=0.3))
    defs = grad("zoneG", [(0, "#8A0F1C", None), (1, "#FF6A74", None)], 0, 0, 1, 0)
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "Les issues en chiffres",
                   f"{len(issues)} issues réparties entre deux développeurs, par priorité, par état et par zone du jeu.")


def palette():
    ts = Typeset()
    W, H = 1000, 640
    defs = patterns() + '<radialGradient id="mythic" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#E0344B" stop-opacity=".7"/><stop offset="1" stop-color="#E0344B" stop-opacity="0"/></radialGradient>'
    body = [f'<rect width="{W}" height="{H}" fill="#07040A"/>']
    swatches = [
        ("Nuit", "#07040A", C["ivory"]), ("Nuit rouge", "#12070B", C["ivory"]), ("Laque", "#1B0A0F", C["ivory"]),
        ("Sang", "#E0344B", "#fff"), ("Sang profond", "#8A0F1C", "#fff"), ("Sang vif", "#FF6A74", "#12070B"),
        ("Ivoire", "#EFE3D0", "#12070B"), ("Or", "#F2C20F", "#12070B"), ("Chair", "#F08A3A", "#12070B"),
        ("Âmes, glycine", "#B06FE0", "#12070B"), ("Pourfendeur", "#2F8FD0", "#fff"), ("Jade", "#5FC9A8", "#12070B"),
    ]
    body.append(ts.text("COULEURS", 12, 24, 12, C["bright"], tracking=3, bold=0.25))
    sw, sh, gap = 76, 96, 6.2
    for i, (name, hexv, ink) in enumerate(swatches):
        x = 12 + i * (sw + gap)
        body.append(f'<path d="M{x + 10} 40 H{x + sw} L{x + sw - 10} {40 + sh} H{x} Z" fill="{hexv}" stroke="#EFE3D0" stroke-opacity=".25"/>')
        body.append(ts.text(name, x + sw / 2, 40 + sh + 16, 10.5, C["ivory"], anchor="middle", opacity=0.9))
        body.append(ts.text(hexv, x + sw / 2, 40 + sh + 30, 9.5, C["ivory"], anchor="middle", opacity=0.5))
    # motifs
    body.append(ts.text("MOTIFS TRADITIONNELS", 12, 214, 12, C["bright"], tracking=3, bold=0.25))
    tiles = [("市松", "Ichimatsu", "damier côté pourfendeur", "url(#ichi-slayer)"), ("市松", "Ichimatsu", "damier côté démon", "url(#ichi-demon)"),
             ("青海波", "Seigaiha", "vagues, l'Eau", "url(#seigaiha)"), ("鱗", "Uroko", "écailles, la Foudre", "url(#uroko)")]
    tw = 232
    for i, (kanji, name, use, fill) in enumerate(tiles):
        x = 12 + i * (tw + 18.7)
        body.append(f'<rect x="{x}" y="228" width="{tw}" height="104" rx="6" fill="{fill}" stroke="#EFE3D0" stroke-opacity=".25"/>')
        body.append(f'<rect x="{x}" y="288" width="{tw}" height="44" rx="0" fill="#07040A" fill-opacity=".78"/>')
        body.append(ts.text(kanji, x + 14, 266, 28, C["ivory"], bold=0.6, extra='opacity=".95"'))
        body.append(ts.text(name, x + 14, 308, 13, C["ivory"], bold=0.3))
        body.append(ts.text(use, x + 14, 324, 10.5, C["ivory"], opacity=0.6))
    # raretés
    body.append(ts.text("SIX RARETÉS DES POUVOIRS (proposition, décision 8)", 12, 366, 12, C["bright"], tracking=3, bold=0.25))
    rar = [("Commun", "#8A8680"), ("Peu commun", "#4FA08A"), ("Rare", "#3D68C2"), ("Épique", "#9A58D0"), ("Légendaire", "#F2C20F"), ("Mythique", "#E0344B")]
    for i, (name, color) in enumerate(rar):
        x = 12 + i * 162
        cx, cy = x + 40, 424
        if name == "Mythique":
            body.append(f'<circle cx="{cx}" cy="{cy}" r="46" fill="url(#mythic)" class="glw"/>')
        body.append(f'<path d="M{cx} {cy - 30} L{cx + 26} {cy - 15} L{cx + 26} {cy + 15} L{cx} {cy + 30} L{cx - 26} {cy + 15} L{cx - 26} {cy - 15} Z" fill="#12070B" stroke="{color}" stroke-width="{2 + i * 0.3:.1f}"/>')
        body.append(f'<path d="M{cx} {cy - 20} L{cx + 17} {cy - 10} L{cx + 17} {cy + 10} L{cx} {cy + 20} L{cx - 17} {cy + 10} L{cx - 17} {cy - 10} Z" fill="{color}" fill-opacity="{0.25 + i * 0.1:.2f}"/>')
        body.append(ts.text(name, cx + 40, cy + 4, 13.5, C["ivory"], bold=0.25))
    # typographie et règles
    body.append(ts.text("TYPOGRAPHIE", 12, 494, 12, C["bright"], tracking=3, bold=0.25))
    x = 12
    for size in (50, 28, 20, 16, 14, 12):
        body.append(ts.text("鬼", x, 548, size, C["ivory"], bold=0.4))
        body.append(ts.text(f"{size}", x, 570, 10.5, C["ivory"], opacity=0.5))
        x += size * 1.0 + 18
    body.append(ts.text("Titres et kanji : Shippori Mincho · interface et chiffres : Rajdhani", 12, 592, 12, C["ivory"], opacity=0.75))
    body.append(ts.text("(ces images : Noto Sans JP, licence libre OFL)", 12, 610, 10.5, C["ivory"], opacity=0.45))
    rules = [("menaçant et élégant, jamais gore", "威"), ("les kanji sont des icônes", "印"), ("tout reste réalisable en HTML et CSS", "技")]
    rx = 560
    body.append(ts.text("RÈGLES", rx, 494, 12, C["bright"], tracking=3, bold=0.25))
    for i, (text, kanji) in enumerate(rules):
        y = 516 + i * 38
        body.append(seal(ts, rx + 18, y + 10, 16, kanji, C["blood"], size=17, bold=0.4, ring=1.6))
        body.append(ts.text(text, rx + 46, y + 15, 14, C["ivory"], opacity=0.9))
    body.append(ts.text("Originalité : aucun personnage, logo ou illustration existant n'est repris.", rx, 632, 11, C["ivory"], opacity=0.5))
    return svg_doc(W, H, "".join(body), defs + ts.defs(), "Direction artistique",
                   "Palette de douze couleurs, quatre motifs traditionnels japonais, six raretés, échelle typographique et règles de la direction artistique.")
