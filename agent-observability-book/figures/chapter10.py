"""Chapter 8 figures: two paths from a question to a number.

Usage: python -m figures.chapter10 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow, box,
                              store, svg, text, tool)


def two_paths():
    """Figure 10.2. Raw SQL guesses meaning; the metric states it."""
    body = [agent(4, 84, 76, 40, "Pick"),
            store(372, 74, 84, 60, "warehouse", fill=PALE),
            # top path: the model writes SQL from the schema
            box(116, 16, 216, 50, fill="#ffffff", r=6),
            text(224, 37, "SQL written from the schema", size=12,
                 weight=600, anchor="middle"),
            text(224, 55, "joins, filters guessed", size=11.5,
                 anchor="middle", fill=MID),
            arrow([(60, 84), (60, 41), (114, 41)]),
            arrow([(332, 41), (414, 41), (414, 72)]),
            # bottom path: the governed metric, compiled
            tool(116, 142, 216, 50, "metric v3, owner merchandising",
                 fill=FILL),
            text(224, 214, "compiled to SQL, same every time",
                 size=11.5, anchor="middle", fill=MID),
            arrow([(60, 124), (60, 167), (114, 167)]),
            arrow([(332, 167), (414, 167), (414, 136)]),
            text(4, 246, "oat milk -> almond milk", size=11.5,
                 mono=True),
            text(300, 246, "46%", size=12, weight=700),
            text(360, 246, "vs", size=11.5, fill=MID),
            text(390, 246, "75%", size=12, weight=700)]
    return svg(256, body)


FIGURES = {"fig-10-1-receipt-strip": lambda: receipt_strip({2}),
           "fig-10-2-two-paths": two_paths}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
