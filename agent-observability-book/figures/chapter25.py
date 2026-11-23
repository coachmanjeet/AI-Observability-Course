"""Chapter 19 figures: the canary and the runbook.

Usage: python -m figures.chapter25 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, arrow, box, gate,
                              svg, text)

STEPS = [("detect", "receipts by version", "+0"),
         ("contain", "approval tier", "+2"),
         ("investigate", "query receipts", "+9"),
         ("recover", "registry rollback", "+13"),
         ("verify", "new receipts", "+14"),
         ("review", "postmortem", "next day")]


def runbook():
    """Figure 25.2. Every step reads or changes recorded state."""
    body = []
    for i, (name, what, when) in enumerate(STEPS):
        col, row = i % 3, i // 3
        x, y = 4 + col * 152, 10 + row * 84
        fill = FILL if name == "contain" else (
            PALE if name == "detect" else "#ffffff")
        body.append(box(x, y, 136, 56, fill=fill, r=6))
        body.append(text(x + 68, y + 20, name, size=12,
                         weight=700, anchor="middle"))
        body.append(text(x + 68, y + 35, what, size=11.5,
                         anchor="middle"))
        body.append(text(x + 68, y + 50, f"{when} min"
                         if when.startswith("+") else when,
                         size=11.5, anchor="middle", fill=MID))
        if col < 2:
            body.append(arrow([(x + 136, y + 28),
                               (x + 150, y + 28)]))
    body.append(arrow([(380, 66), (380, 78), (72, 78), (72, 92)]))
    return svg(10 + 84 + 56 + 8, body)


FIGURES = {"fig-25-1-receipt-strip": lambda: receipt_strip({0}),
           "fig-25-2-runbook": runbook}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
