"""Aperçu : rend une image SVG en PNG avec Microsoft Edge sans interface, comme un lecteur la verrait dans un <img> (sert à vérifier le travail)."""
import subprocess
import tempfile
from pathlib import Path

EDGE = next((p for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"), Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")) if p.exists()), None)


def to_png(svg_path, png_path, width, height, scale=1, background="0D1117", wait_ms=1500, dark=True):
    """Rend l'image à sa taille (width x height) sur un fond uni, puis écrit le PNG."""
    if EDGE is None:
        raise SystemExit("Microsoft Edge introuvable")
    svg_path, png_path = Path(svg_path).resolve(), Path(png_path).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(
            f'<!doctype html><meta charset="utf-8"><body style="margin:0;background:#{background}"><img src="{svg_path.as_uri()}" width="{width}" height="{height}" style="display:block"></body>',
            encoding="utf-8",
        )
        if png_path.exists():
            png_path.unlink()
        subprocess.run(
            [str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
             f"--virtual-time-budget={wait_ms}", f"--default-background-color={background}FF", f"--screenshot={png_path}", page.as_uri()],
            check=False, capture_output=True, timeout=120,
        )
    return png_path if png_path.exists() else None
