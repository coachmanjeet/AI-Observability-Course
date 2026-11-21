"""Chapter 11 figures: a context pack and its release line.

Usage: python -m figures.chapter11 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, arrow, boundary, box,
                              gate, svg, text)


def pack_and_gate():
    """Figure 11.2. What a pack holds, and how it goes live."""
    body = [boundary(4, 8, 180, 196, "pronto-support 1.5.0")]
    for i, label in enumerate(("instructions.md",
                               "skills/spoiled-food.md",
                               "refund policy, 2026-11-16",
                               "order and photo records")):
        y = 36 + i * 36
        body += [box(16, y, 156, 28, fill=PALE if i < 2 else FILL),
                 text(24, y + 19, label, size=11.5)]
    body += [text(94, 196, "digests + signature", size=11.5,
                  anchor="middle", fill=MID),
             arrow([(186, 106), (226, 106)]),
             gate(258, 106, 30),
             text(258, 110, "gate", size=11.5, weight=600,
                  anchor="middle"),
             text(258, 154, "consistency,", size=11.5,
                  anchor="middle", fill=MID),
             text(258, 168, "golden cases", size=11.5,
                  anchor="middle", fill=MID),
             arrow([(290, 106), (316, 106)])]
    # the release line
    rows = [("1.4.0", "live", 40), ("1.5.0-rc1", "blocked", 82),
            ("1.5.0", "live", 124), ("1.4.0", "rollback", 166)]
    for v, state, y in rows:
        fill = FILL if state == "live" else "#ffffff"
        body += [box(320, y - 16, 136, 30, fill=fill, r=5),
                 text(328, y + 4, v, size=11.5, mono=True),
                 text(450, y + 4, state, size=11.5, anchor="end",
                      fill=MID if state != "live" else "#000000")]
    return svg(214, body)


FIGURES = {"fig-11-1-receipt-strip": lambda: receipt_strip({2}),
           "fig-11-2-pack-and-gate": pack_and_gate}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
