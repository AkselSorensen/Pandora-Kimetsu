"""Texte -> contours vectoriels, pour que les images SVG du dépôt ne dépendent d'aucune police installée chez le lecteur.

Police utilisée : Noto Sans JP (licence SIL OFL 1.1, https://fonts.google.com/noto/specimen/Noto+Sans+JP), qui couvre le latin accentué
et tous les kanji du projet. Le fichier est cherché dans la variable d'environnement PK_FONT_NOTO, puis aux emplacements connus.
"""
import os
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

CANDIDATES = [
    os.environ.get("PK_FONT_NOTO", ""),
    str(Path(__file__).resolve().parent / "fonts" / "NotoSansJP-Regular.otf"),
    r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\shareplay\resources\notosansjp-regular.otf",
    str(Path.home() / ".fonts" / "NotoSansJP-Regular.otf"),
]


def find_font():
    for candidate in CANDIDATES:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit("Police introuvable : télécharge Noto Sans JP (OFL) et pointe PK_FONT_NOTO vers NotoSansJP-Regular.otf")


BLANKS = (" ", " ", " ")  # espaces insécables : dessinés comme du vide, un peu plus étroits qu'une espace


class Typeset:
    """Une instance par image : elle note les glyphes utilisés et les déclare une seule fois dans <defs>."""

    def __init__(self):
        self.font = TTFont(find_font())
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.hmtx = self.font["hmtx"]
        self.upm = self.font["head"].unitsPerEm
        self.used = {}

    def _name(self, char):
        name = self.cmap.get(ord(char))
        if name is None:
            raise SystemExit(f"Glyphe absent de la police : {char!r}")
        return name

    def advance(self, char):
        if char in BLANKS:
            return self.hmtx[self._name(" ")][0] * 0.62
        return self.hmtx[self._name(char)][0]

    def width(self, text, size, tracking=0.0):
        return sum(self.advance(c) for c in text) / self.upm * size + tracking * max(0, len(text) - 1)

    def wrap(self, text, size, max_width, tracking=0.0):
        """Découpe un texte en lignes qui tiennent dans max_width (aux espaces ; les kanji se coupent n'importe où)."""
        lines, line = [], ""
        for word in text.split(" "):
            trial = (line + " " + word) if line else word
            if self.width(trial, size, tracking) <= max_width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def _glyph_id(self, char):
        name = self._name(char)
        gid = f"g{ord(char):x}"
        if gid not in self.used:
            pen = SVGPathPen(self.glyphs, ntos=lambda v: str(int(round(v))))
            self.glyphs[name].draw(pen)
            self.used[gid] = pen.getCommands()
        return gid

    def text(self, text, x, y, size, fill="#EFE3D0", anchor="start", bold=0.0, tracking=0.0, opacity=None, extra=""):
        """Ligne de texte dont la ligne de base est à y. bold : épaisseur de contour ajoutée, en pixels."""
        total = self.width(text, size, tracking)
        cursor = x - (total / 2 if anchor == "middle" else total if anchor == "end" else 0)
        scale = size / self.upm
        attrs = f'fill="{fill}"'
        if bold:
            attrs += f' stroke="{fill}" stroke-width="{bold / scale:.0f}" stroke-linejoin="round"'
        if opacity is not None:
            attrs += f' opacity="{opacity}"'
        uses = []
        for char in text:
            if char != " " and char not in BLANKS:
                uses.append(f'<use href="#{self._glyph_id(char)}" transform="translate({cursor:.1f} {y:.1f}) scale({scale:.5f} {-scale:.5f})"/>')
            cursor += self.advance(char) * scale + tracking
        return f'<g {attrs} {extra}>' + "".join(uses) + "</g>"

    def lines(self, text, x, y, size, max_width, leading=1.4, **kwargs):
        """Paragraphe : renvoie le markup et la hauteur utilisée."""
        out, count = [], 0
        for count, line in enumerate(self.wrap(text, size, max_width, kwargs.get("tracking", 0.0)), start=1):
            out.append(self.text(line, x, y + (count - 1) * size * leading, size, **kwargs))
        return "".join(out), count * size * leading

    def defs(self):
        return "".join(f'<path id="{gid}" d="{d}"/>' for gid, d in self.used.items())
