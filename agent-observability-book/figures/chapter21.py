"""Chapter 16 figures: autonomy tiers and responses.

Usage: python -m figures.chapter21 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import FILL, MID, PALE, arrow, box, svg, text

RUNGS = [("act autonomously", "up to $10", "watched in aggregate"),
         ("sampled review", "$10 to $50", "5% checked after"),
         ("act with approval", "$50 to $500", "a lead approves first"),
         ("suggest only", "over $500", "a person acts")]
STEPS = ["monitor", "restrict", "pause", "revoke"]


def ladder():
    """Figure 21.2. The ladder, and the way back down."""
    body, y = [], 20
    for i, (tier, amount, human) in enumerate(reversed(RUNGS)):
        x = 4 + (3 - i) * 22
        fill = [PALE, "#ffffff", FILL, "#ffffff"][i]
        body.append(box(x, y, 300 - (3 - i) * 22, 36, fill=fill,
                        r=4))
        body.append(text(x + 8, y + 15, tier, size=12,
                         weight=600))
        body.append(text(x + 8, y + 30, f"{amount}: {human}",
                         size=11.5, fill=MID))
        y += 44
    body.append(text(330, 20, "if something", size=11.5,
                     fill=MID))
    body.append(text(330, 34, "goes wrong", size=11.5, fill=MID))
    yy = 50
    for step in STEPS:
        body.append(box(330, yy, 100, 24, r=12))
        body.append(text(380, yy + 16, step, size=11.5,
                         anchor="middle"))
        if step != STEPS[-1]:
            body.append(arrow([(380, yy + 24), (380, yy + 34)]))
        yy += 34
    return svg(y + 8, body)


FIGURES = {"fig-21-1-receipt-strip": lambda: receipt_strip({3}),
           "fig-21-2-autonomy-ladder": ladder}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
