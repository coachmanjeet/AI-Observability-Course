"""Chapter 21 figures: the driver tree.

Usage: python -m figures.chapter27 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import FILL, MID, PALE, box, line, svg, text

TOP = ("resolved in 7 days", "89.3%, $0.336 each")
MID_ROW = [("refunded", "549"), ("came back", "163"),
           ("escalated", "137")]
LOW_ROW = [("model cost", "$0.015 a conv"),
           ("timeouts", "26 came back"),
           ("people", "$5.80 a contact")]


def driver_tree():
    """Figure 27.2. Business, behavior, technology."""
    body = [box(130, 6, 200, 44, fill=FILL, r=6),
            text(230, 24, TOP[0], size=12, weight=700,
                 anchor="middle"),
            text(230, 41, TOP[1], size=11.5, anchor="middle"),
            text(4, 30, "business", size=11.5, fill=MID)]
    for i, (a, b) in enumerate(MID_ROW):
        x = 64 + i * 128
        body += [line([(230, 50), (x + 56, 74)], width=0.9),
                 box(x, 74, 112, 40, fill=PALE, r=6),
                 text(x + 56, 90, a, size=12, weight=600,
                      anchor="middle"),
                 text(x + 56, 106, b, size=11.5,
                      anchor="middle")]
    body.append(text(4, 98, "behavior", size=11.5, fill=MID))
    for i, (a, b) in enumerate(LOW_ROW):
        x = 64 + i * 128
        body += [line([(x + 56, 114), (x + 56, 138)], width=0.9),
                 box(x, 138, 112, 40, r=6),
                 text(x + 56, 154, a, size=12, weight=600,
                      anchor="middle"),
                 text(x + 56, 170, b, size=11.5,
                      anchor="middle")]
    body.append(text(4, 162, "technical", size=11.5, fill=MID))
    return svg(186, body)


FIGURES = {"fig-27-1-receipt-strip": lambda: receipt_strip({4}),
           "fig-27-2-driver-tree": driver_tree}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
