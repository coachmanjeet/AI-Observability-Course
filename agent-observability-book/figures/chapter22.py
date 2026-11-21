"""Chapter 22 figures: four ways to wire the same task.

Usage: python -m figures.chapter22 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (DASH, MID, PALE, agent, arrow, box,
                              svg, text)

W, H = 226, 112


def node(x, y, label, kind="1P", fill="#ffffff"):
    return agent(x, y, 64, 26, label, kind=kind, fill=fill,
                 size=11.5)


def panel(x0, y0, title, nodes, edges):
    out = [box(x0, y0, W - 6, H - 6, r=4, fill="none"),
           text(x0 + 8, y0 + 16, title, size=12, weight=700)]
    for (x, y, label, kind, fill) in nodes:
        out.append(node(x0 + x, y0 + y, label, kind, fill))
    for (pts, by_model) in edges:
        p = [(x0 + a, y0 + b) for a, b in pts]
        out.append(arrow(p, dash=DASH if by_model else None))
    return out


def topologies():
    """Figure 22.2. Solid: code routes. Dashed: a model does."""
    body = []
    body += panel(0, 0, "router", [
        (78, 26, "Router", "1P", PALE),
        (10, 72, "Speedy", "1P", "#ffffff"),
        (146, 72, "Ledger", "3P", "#ffffff")],
        [([(96, 52), (60, 70)], False),
         ([(124, 52), (166, 70)], False)])
    body += panel(W, 0, "supervisor", [
        (78, 26, "Concierge", "1P", PALE),
        (10, 72, "Speedy", "1P", "#ffffff"),
        (146, 72, "Ledger", "3P", "#ffffff")],
        [([(96, 52), (60, 70)], True),
         ([(124, 52), (166, 70)], True)])
    body += panel(0, H, "handoff", [
        (10, 50, "Speedy", "1P", "#ffffff"),
        (146, 50, "Ledger", "3P", "#ffffff")],
        [([(74, 63), (144, 63)], True)])
    body += panel(W, H, "broker", [
        (10, 26, "Speedy", "1P", "#ffffff"),
        (10, 72, "Broker", "1P", PALE),
        (146, 26, "Ledger", "3P", "#ffffff"),
        (146, 72, "Promo", "3P", "#ffffff")],
        [([(42, 52), (42, 70)], True),
         ([(74, 80), (144, 44)], True),
         ([(74, 86), (144, 86)], True)])
    y = 2 * H + 6
    body += [arrow([(4, y + 6), (40, y + 6)]),
             text(46, y + 10, "code chooses", size=11.5,
                  fill=MID),
             arrow([(150, y + 6), (186, y + 6)], dash=DASH),
             text(192, y + 10, "a model chooses", size=11.5,
                  fill=MID),
             box(320, y, 22, 12, r=3, kind="3P"),
             text(348, y + 10, "third party", size=11.5,
                  fill=MID)]
    return svg(y + 22, body)


FIGURES = {"fig-22-1-receipt-strip": lambda: receipt_strip({4}),
           "fig-22-2-topologies": topologies}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
