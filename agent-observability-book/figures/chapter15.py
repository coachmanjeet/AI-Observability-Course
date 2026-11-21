"""Chapter 15 figures: a registry record's lifecycle.

Usage: python -m figures.chapter15 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, arrow, box, gate, svg,
                              text)

STATES = [("draft", 4), ("in review", 98), ("approved", 210),
          ("deprecated", 316)]


def lifecycle():
    """Figure 15.2. States, and what each move requires."""
    body = []
    for name, x in STATES:
        fill = FILL if name == "approved" else PALE
        body += [box(x, 40, 84, 36, fill=fill, r=18),
                 text(x + 42, 63, name, size=12, weight=600,
                      anchor="middle")]
    body += [arrow([(88, 58), (96, 58)]),
             arrow([(182, 58), (194, 58)]),
             gate(201, 58, 9),
             arrow([(294, 58), (314, 58)]),
             box(372, 120, 84, 36, fill="#ffffff", r=18),
             text(414, 143, "retired", size=12, weight=600,
                  anchor="middle"),
             arrow([(358, 76), (390, 118)]),
             arrow([(46, 76), (46, 138), (370, 138)], kind="trace"),
             text(140, 132, "unclaimed", size=11.5, fill=MID,
                  anchor="middle"),
             text(4, 20, "claimed by an owner", size=11.5, fill=MID),
             text(170, 20, "owner, version, tier;", size=11.5,
                  fill=MID),
             text(170, 34, "high tier: security review", size=11.5,
                  fill=MID),
             text(4, 186, "Every move is a recorded decision: "
                  "who, why, when.", size=11.5, weight=600)]
    return svg(196, body)


FIGURES = {"fig-15-1-receipt-strip": lambda: receipt_strip({0}),
           "fig-15-2-lifecycle": lifecycle}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
