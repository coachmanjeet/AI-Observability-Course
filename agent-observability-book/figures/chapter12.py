"""Chapter 12 figures: memory with boundaries.

Usage: python -m figures.chapter12 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow,
                              boundary, box, gate, receipt, svg,
                              text)


def boundaries():
    """Figure 12.2. Scoped, expiring, quarantined, erasable."""
    body = [agent(4, 92, 80, 40, "Speedy"),
            gate(132, 112, 22),
            text(132, 116, "write", size=11.5, anchor="middle"),
            arrow([(84, 112), (108, 112)]),
            boundary(184, 8, 272, 96, "mem://…/cust_7f3a91"),
            box(196, 34, 248, 26, fill=PALE),
            text(204, 52, "preference, 180 days", size=11.5),
            box(196, 66, 248, 26, fill=FILL),
            text(204, 84, "history, 30 days (expires)", size=11.5),
            boundary(184, 120, 272, 66, "mem://…/cust_2c88e4"),
            box(196, 146, 248, 26, fill="#ffffff"),
            text(204, 164, "claim: quarantined", size=11.5,
                 weight=600),
            arrow([(154, 112), (182, 70)]),
            arrow([(154, 112), (182, 156)]),
            receipt(184, 200, 130, 46, fill="#ffffff"),
            text(249, 220, "tombstone", size=11.5, weight=600,
                 anchor="middle"),
            text(249, 236, "count + digest", size=11.5,
                 anchor="middle"),
            text(326, 226, "after erasure", size=11.5, fill=MID),
            text(4, 160, "reads stay in", size=11.5, fill=MID),
            text(4, 175, "one scope", size=11.5, fill=MID)]
    return svg(256, body)


FIGURES = {"fig-12-1-receipt-strip": lambda: receipt_strip({2}),
           "fig-12-2-memory-boundaries": boundaries}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
