"""Chapter 26 figures: one surface, three kinds of caller.

Usage: python -m figures.chapter26 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow,
                              boundary, box, gate, receipt, svg,
                              text, tool)

CALLERS = [("Shopper Assistant", "3P", "signed, granted"),
           ("Reseller Buyer", "3P", "signed, partner"),
           ("unknown client", "shadow", "unsigned")]
TIERS = [("public", "catalog.search", PALE),
         ("delegated", "cart.add, orders.place", "#ffffff"),
         ("confirm", "orders over $150", FILL)]


def surface():
    """Figure 26.2. Identify, tier, delegate, confirm, record."""
    body = []
    for i, (name, kind, note) in enumerate(CALLERS):
        y = 12 + i * 58
        body.append(agent(4, y, 130, 34, name, kind=kind,
                          size=11.5))
        body.append(text(69, y + 48, note, size=11.5,
                         anchor="middle", fill=MID))
        body.append(arrow([(134, y + 17), (176, 88 + i * 8)]))
    body.append(gate(212, 96, 30))
    body.append(text(212, 100, "surface", size=11.5,
                     anchor="middle"))
    body.append(boundary(256, 8, 200, 162, "pronto-shop MCP"))
    for i, (tier, tools, fill) in enumerate(TIERS):
        y = 30 + i * 44
        body.append(box(266, y, 180, 36, fill=fill, r=4))
        body.append(text(274, y + 15, tier, size=12,
                         weight=700))
        body.append(text(274, y + 30, tools, size=11.5))
        body.append(arrow([(242, 96), (264, y + 18)]))
    body.append(receipt(300, 180, 120, 32))
    body.append(text(360, 200, "receipt: agent", size=11.5,
                     anchor="middle"))
    body.append(text(360, 228, "+ customer + session",
                     size=11.5, anchor="middle", fill=MID))
    return svg(238, body)


FIGURES = {"fig-26-1-receipt-strip": lambda: receipt_strip({0, 1}),
           "fig-26-2-surface": surface}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
