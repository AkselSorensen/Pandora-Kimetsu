"""Palette, motifs japonais, animations et enveloppe SVG communs à toutes les images du README.

La direction artistique vient de docs/DA-DEMON.md : le noir teinté de sang, la lune rouge, l'ivoire, l'or ; côté pourfendeur, le bleu
glacier. Les motifs (ichimatsu, seigaiha, uroko) sont des motifs traditionnels japonais, du domaine public : aucun visuel de l'œuvre n'est repris.
"""
from html import escape

C = dict(
    night0="#07040A", night1="#12070B", night2="#1B0A0F", night3="#2A1018",
    blood="#E0344B", deep="#8A0F1C", bright="#FF6A74",
    ivory="#EFE3D0", moon="#E4CBA8", gold="#F2C20F", flesh="#F08A3A", soul="#B06FE0",
    slayer="#2F8FD0", ice="#8CC8F0", jade="#5FC9A8", stone="#A8A29A",
)

BASE_STYLE = """
@keyframes pulse{0%,100%{opacity:.55}50%{opacity:1}}
@keyframes heart{0%,100%{transform:scale(1)}12%{transform:scale(1.07)}24%{transform:scale(1)}36%{transform:scale(1.05)}48%{transform:scale(1)}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes dash{to{stroke-dashoffset:-48}}
@keyframes sweep{0%{transform:translateX(-340px)}55%,100%{transform:translateX(1340px)}}
@keyframes glow{0%,100%{opacity:.35}50%{opacity:.8}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes rise{from{transform:scaleY(0)}to{transform:scaleY(1)}}
.hb{transform-box:fill-box;transform-origin:center;animation:heart 3.4s ease-in-out infinite}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 80s linear infinite}
.flt{animation:float 5s ease-in-out infinite}
.pls{animation:pulse 4s ease-in-out infinite}
.glw{animation:glow 4.5s ease-in-out infinite}
.dsh{stroke-dasharray:6 6;animation:dash 1.6s linear infinite}
.bar{transform-box:fill-box;transform-origin:left center;animation:grow 1.4s cubic-bezier(.2,.8,.2,1) both}
.col{transform-box:fill-box;transform-origin:center bottom;animation:rise 1.2s cubic-bezier(.2,.8,.2,1) both}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def svg_doc(width, height, body, defs="", title="", desc="", style=""):
    """Enveloppe d'une image : accessible (title et desc), sans police externe, animations coupées si l'utilisateur le demande."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="t d">'
        f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
        f"<defs>{defs}</defs><style>{BASE_STYLE}{style}</style>{body}</svg>\n"
    )


def patterns():
    """Motifs réutilisables : ichimatsu (damier), seigaiha (vagues), uroko (écailles)."""
    return f"""
<pattern id="ichi-slayer" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="#050E0C"/><rect width="20" height="20" fill="#0F3B30"/><rect x="20" y="20" width="20" height="20" fill="#0F3B30"/></pattern>
<pattern id="ichi-demon" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="#12070B"/><rect width="20" height="20" fill="#5A0E18"/><rect x="20" y="20" width="20" height="20" fill="#5A0E18"/></pattern>
<pattern id="ichi-gold" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="#120C03"/><rect width="20" height="20" fill="#3A2A06"/><rect x="20" y="20" width="20" height="20" fill="#3A2A06"/></pattern>
<pattern id="seigaiha" width="48" height="24" patternUnits="userSpaceOnUse">
<g fill="#06131D" stroke="#2F8FD0" stroke-width="1.2" stroke-opacity=".55">
<circle cx="0" cy="12" r="22"/><circle cx="0" cy="12" r="15"/><circle cx="0" cy="12" r="8"/>
<circle cx="48" cy="12" r="22"/><circle cx="48" cy="12" r="15"/><circle cx="48" cy="12" r="8"/>
<circle cx="24" cy="24" r="22"/><circle cx="24" cy="24" r="15"/><circle cx="24" cy="24" r="8"/></g></pattern>
<pattern id="uroko" width="36" height="31" patternUnits="userSpaceOnUse"><rect width="36" height="31" fill="#120C03"/>
<path d="M0 31 L18 0 L36 31 Z" fill="#3A2A06" stroke="#F2C20F" stroke-opacity=".35" stroke-width="1"/></pattern>
<pattern id="scale-blood" width="36" height="31" patternUnits="userSpaceOnUse"><rect width="36" height="31" fill="#12070B"/>
<path d="M0 31 L18 0 L36 31 Z" fill="#2A0A12" stroke="#E0344B" stroke-opacity=".3" stroke-width="1"/></pattern>
"""


def ink_filter():
    """Contour légèrement irrégulier, comme un trait de pinceau sur du papier."""
    return '<filter id="ink" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="5"/></filter>'


def grad(gid, stops, x1=0, y1=0, x2=0, y2=1, units="objectBoundingBox"):
    body = "".join(f'<stop offset="{o}" stop-color="{c}"' + (f' stop-opacity="{a}"' if a is not None else "") + "/>" for o, c, a in stops)
    return f'<linearGradient id="{gid}" gradientUnits="{units}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{body}</linearGradient>'


def radial(gid, stops, cx=0.5, cy=0.5, r=0.5):
    body = "".join(f'<stop offset="{o}" stop-color="{c}"' + (f' stop-opacity="{a}"' if a is not None else "") + "/>" for o, c, a in stops)
    return f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">{body}</radialGradient>'


def clipped_corners(x, y, w, h, cut=14):
    """Rectangle aux coins coupés en biais, comme une plaque de laque."""
    return f"M{x + cut} {y} H{x + w - cut} L{x + w} {y + cut} V{y + h - cut} L{x + w - cut} {y + h} H{x + cut} L{x} {y + h - cut} V{y + cut} Z"


PETAL = "M0 0 C4 -5 11 -3 10 3 C9 8 3 8 0 0Z"


def petals(count, width, height, seed=3, colors=("#B06FE0", "#8E4EC6", "#C99BEF"), prefix="p"):
    """Pétales de glycine qui tombent : positions et durées pseudo-aléatoires mais stables d'une génération à l'autre."""
    import random

    rnd = random.Random(seed)
    out, css = [], []
    for i in range(count):
        x = rnd.uniform(0, width)
        dur = rnd.uniform(9, 17)
        delay = -rnd.uniform(0, dur)
        drift = rnd.uniform(-90, 60)
        scale = rnd.uniform(0.55, 1.25)
        rot = rnd.choice([-1, 1]) * rnd.uniform(200, 520)
        color = rnd.choice(colors)
        css.append(
            f"@keyframes {prefix}{i}{{from{{transform:translate({x:.0f}px,-24px) rotate(0deg) scale({scale:.2f})}}"
            f"to{{transform:translate({x + drift:.0f}px,{height + 24}px) rotate({rot:.0f}deg) scale({scale:.2f})}}}}"
            f".{prefix}{i}{{animation:{prefix}{i} {dur:.1f}s linear {delay:.1f}s infinite}}"
        )
        out.append(f'<path d="{PETAL}" fill="{color}" opacity="{rnd.uniform(.45, .9):.2f}" class="{prefix}{i}" style="transform:translate({x:.0f}px,{height + 30}px)"/>')
    return "".join(out), "".join(css)
