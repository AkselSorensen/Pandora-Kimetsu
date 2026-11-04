import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import art_banner, art_world, art_demon, art_system
from render import to_png
OUT = Path(r"C:\Users\azrae\AppData\Local\Temp\claude\687c9a36d921bff3\1100d7b0-e605-4318-82c3-0e21b56e90bf\scratchpad\art")
OUT.mkdir(exist_ok=True)
jobs = {
    "chapter1": (art_world.chapter(0), 1000, 84), "chapter11": (art_world.chapter(10), 1000, 84),
    "stats": (art_demon.stats(), None, None), "loop": (art_demon.loop(), None, None), "devour": (art_demon.devour(), None, None),
    "architecture": (art_system.architecture(), None, None), "pipeline": (art_system.pipeline(), None, None), "roadmap": (art_system.roadmap(), None, None),
    "progress": (art_system.progress(), None, None), "palette": (art_system.palette(), None, None),
    "camps": (art_world.camps(), 1000, 520), "breaths": (art_world.breaths(), None, None), "journey": (art_world.journey(), 1000, 380),
}
only = sys.argv[1:] or list(jobs)
for name in only:
    svg, w, h = jobs[name]
    (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    svg_static = svg.replace("</svg>", "<style>*{animation:none!important}</style></svg>")
    (OUT / f"{name}_static.svg").write_text(svg_static, encoding="utf-8")
    if w is None:
        import re
        m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg); w, h = int(m[1]), int(m[2])
    print(name, to_png(OUT / f"{name}_static.svg", OUT / f"{name}.png", w, h, 1, wait_ms=2500), len(svg) // 1024, "Ko")
