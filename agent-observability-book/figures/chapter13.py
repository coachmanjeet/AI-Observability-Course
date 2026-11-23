"""Chapter 10 figures: filter before context, not in it.

Usage: python -m figures.chapter13 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow, box,
                              gate, store, svg, text, tool)


def filter_first():
    """Figure 13.2. Three agents, one server, three views."""
    body = [store(4, 84, 84, 64, "orders,", fill=PALE),
            text(46, 140, "customers", size=11.5, anchor="middle"),
            tool(118, 72, 112, 88, "MCP server"),
            gate(174, 186, 20),
            text(174, 228, "row and field", size=11.5,
                 anchor="middle", fill=MID),
            text(174, 242, "filter per principal", size=11.5,
                 anchor="middle", fill=MID),
            arrow([(88, 116), (116, 116)]),
            line_to(174, 160, 174, 166)]
    views = [("Speedy", "for cust_7f3a91", "2 of 6 orders", 24),
             ("Pick", "for merchandising", "no personal data", 98),
             ("Promo", "for marketing", "3 of 5, opted in", 172)]
    for name, who, sees, y in views:
        body += [arrow([(232, 116), (258, y + 18)]),
                 agent(260, y, 68, 36, name,
                       kind="3P" if name == "Promo" else "1P"),
                 text(334, y + 14, who, size=11.5, fill=MID),
                 text(334, y + 30, sees, size=11.5, weight=600)]
    return svg(252, body)


def line_to(x1, y1, x2, y2):
    from figures.notation import line
    return line([(x1, y1), (x2, y2)], width=1.0)


FIGURES = {"fig-13-1-receipt-strip": lambda: receipt_strip({1, 2}),
           "fig-13-2-filter-first": filter_first}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
