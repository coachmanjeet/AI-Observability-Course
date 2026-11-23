"""Chapter 13 figures: granted versus used.

Usage: python -m figures.chapter18 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import FILL, MID, PALE, box, svg, text
from policy.privilege import RISKY, review

CELL, X0 = 46, 80


def diff():
    """Figure 18.2. Each square is one grant."""
    body, y = [], 14
    for agent, r in review().items():
        body.append(text(4, y + 20, agent.capitalize(), size=12,
                         weight=600))
        order = r["used"] + [s for s in r["unused"]
                             if s not in RISKY] + r["risky_unused"]
        for i, s in enumerate(order):
            fill = (FILL if s in r["used"] else
                    PALE if s in RISKY else "#ffffff")
            kind = "3P" if s in r["risky_unused"] else None
            body.append(box(X0 + i * CELL, y, CELL - 6, 28,
                            fill=fill, r=3, kind=kind))
        y += 40
    y += 4
    legend = [(FILL, None, "used in 30 days"),
              ("#ffffff", None, "unused"),
              (PALE, "3P", "unused and risky")]
    for x, (fill, kind, label) in zip((4, 150, 250), legend):
        body.append(box(x, y, 18, 18, fill=fill, r=3, kind=kind))
        body.append(text(x + 24, y + 14, label, size=11.5,
                         fill=MID))
    return svg(y + 30, body)


FIGURES = {"fig-18-1-receipt-strip": lambda: receipt_strip({1}),
           "fig-18-2-permission-diff": diff}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
