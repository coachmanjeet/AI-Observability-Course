"""Chapter 33 figures: inside the authorization boundary.

Usage: python -m figures.chapter33 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (DASH, MID, PALE, agent, arrow,
                              boundary, store, svg, text, tool)


def inside():
    """Figure 33.2. Components inside; signed imports only."""
    body = [boundary(4, 8, 274, 208, "pronto-gov boundary"),
            boundary(300, 8, 158, 208, "commercial regions"),
            agent(14, 36, 110, 36, "Speedy"),
            tool(12, 96, 82, 34, "model-a"),
            tool(100, 96, 82, 34, "orders MCP"),
            store(12, 150, 82, 44, "receipts", fill=PALE),
            tool(100, 154, 82, 34, "FIPS key"),
            tool(188, 40, 84, 34, "pack mirror"),
            store(188, 96, 84, 44, "collector", fill=PALE),
            tool(188, 158, 84, 34, "eval judge"),
            arrow([(50, 72), (50, 94)]),
            arrow([(100, 72), (130, 94)]),
            arrow([(186, 57), (126, 55)]),
            tool(316, 40, 126, 34, "pack registry"),
            text(379, 90, "signed import only", size=11.5,
                 anchor="middle", fill=MID),
            tool(316, 102, 126, 34, "SaaS tracing"),
            tool(316, 158, 126, 34, "commercial model"),
            arrow([(314, 57), (274, 57)]),
            arrow([(274, 119), (312, 119)], dash=DASH),
            text(293, 113, "×", size=16, weight=700,
                 anchor="middle"),
            arrow([(274, 175), (312, 175)], dash=DASH),
            text(293, 169, "×", size=16, weight=700,
                 anchor="middle")]
    body.append(text(4, 236, "× blocked: traces and eval "
                     "calls stay inside the boundary", size=11.5,
                     fill=MID))
    return svg(244, body)


FIGURES = {"fig-33-1-receipt-strip": lambda: receipt_strip({6}),
           "fig-33-2-boundary": inside}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
