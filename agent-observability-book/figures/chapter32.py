"""Chapter 25 figures: what may cross the border.

Usage: python -m figures.chapter32 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (DASH, FILL, MID, PALE, agent, arrow,
                              boundary, box, store, svg, text, tool)


def border():
    """Figure 32.2. Personal data stays; public data may come."""
    body = [boundary(4, 8, 214, 208, "EU: Fresca's residency"),
            boundary(262, 8, 196, 208, "US regions"),
            agent(60, 40, 104, 36, "Speedy"),
            tool(18, 100, 88, 34, "model, eu-c-1"),
            tool(116, 100, 88, 34, "orders MCP"),
            store(18, 150, 88, 44, "receipts", fill=PALE),
            store(116, 150, 88, 44, "traces", fill=PALE),
            arrow([(96, 76), (62, 98)]),
            arrow([(128, 76), (160, 98)]),
            tool(300, 40, 120, 34, "context pack"),
            text(360, 88, "public: may come in", size=11.5,
                 anchor="middle", fill=MID),
            tool(300, 106, 120, 34, "model, us-w-2"),
            store(300, 154, 120, 44, "analytics", fill=PALE),
            arrow([(298, 57), (166, 57)]),
            arrow([(206, 117), (296, 123)], dash=DASH),
            text(250, 116, "×", size=16, weight=700,
                 anchor="middle"),
            arrow([(206, 172), (296, 176)], dash=DASH),
            text(250, 170, "×", size=16, weight=700,
                 anchor="middle")]
    body.append(text(4, 236, "× personal data blocked from "
                     "leaving, even on failover", size=11.5,
                     fill=MID))
    return svg(244, body)


FIGURES = {"fig-32-1-receipt-strip": lambda: receipt_strip({6}),
           "fig-32-2-residency": border}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
