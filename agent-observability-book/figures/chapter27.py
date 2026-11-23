"""Chapter 21 figures: the driver tree.

Usage: python -m figures.chapter27 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, box, boundary, line,
                              svg, text)

TOP = ("2,800 first contacts = 2,500 + 163 + 137",
       "2,628 confirmed customer resolutions")
MID_ROW = [("resolved by Speedy", "2,500, 89.3%"),
           ("came back", "163"),
           ("escalated", "137; 128 confirmed")]
LOW_ROW = [("refunds 549", "536 resolved, 13 came back"),
           ("timeouts 32", "26 came back, 6 resolved")]


def driver_tree():
    """Figure 21.1. One cohort split three ways that add up, and two
    drivers that cut across the split."""
    body = [box(80, 6, 300, 44, fill=FILL, r=6),
            text(230, 24, TOP[0], size=12, weight=700,
                 anchor="middle"),
            text(230, 41, TOP[1], size=11.5, anchor="middle"),
            text(4, 30, "business", size=11.5, fill=MID)]
    for i, (a, b) in enumerate(MID_ROW):
        x = 62 + i * 132
        body += [line([(230, 50), (x + 62, 74)], width=0.9),
                 box(x, 74, 124, 40, fill=PALE, r=6),
                 text(x + 62, 90, a, size=12, weight=600,
                      anchor="middle"),
                 text(x + 62, 106, b, size=11.5,
                      anchor="middle")]
    body.append(text(4, 98, "behavior", size=11.5, fill=MID))
    body.append(boundary(66, 126, 390, 84,
                         "drivers that overlap the groups"))
    for i, (a, b) in enumerate(LOW_ROW):
        x = 72 + i * 190
        body += [box(x, 148, 182, 40, r=6),
                 text(x + 91, 164, a, size=12, weight=600,
                      anchor="middle"),
                 text(x + 91, 180, b, size=11.5,
                      anchor="middle")]
    body.append(text(4, 172, "technical", size=11.5, fill=MID))
    return svg(216, body)


FIGURES = {"fig-27-1-receipt-strip": lambda: receipt_strip({4}),
           "fig-27-2-driver-tree": driver_tree}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
