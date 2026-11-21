"""Chapter 19 figures: policy at the action boundary.

Usage: python -m figures.chapter19 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow,
                              boundary, box, gate, receipt, store,
                              svg, text, tool)


def boundary_fig():
    """Figure 19.2. The gateway asks; Cedar decides."""
    body = [boundary(2, 14, 116, 84, "agent runtime"),
            agent(14, 40, 92, 40, "Speedy"),
            arrow([(106, 60), (176, 60)]),
            text(148, 52, "tool call", size=11.5,
                 anchor="middle"),
            gate(208, 60, 31),
            text(208, 64, "gateway", size=11.5,
                 anchor="middle"),
            arrow([(208, 91), (208, 124)]),
            text(214, 112, "request", size=11.5),
            tool(160, 126, 96, 44, "Cedar"),
            store(30, 124, 92, 48, "entities", fill=PALE),
            text(76, 188, "registry, orders, token", size=11.5,
                 anchor="middle", fill=MID),
            arrow([(122, 148), (158, 148)], kind="trace"),
            box(270, 126, 70, 44, fill=PALE, r=4),
            text(305, 145, "policy set", size=11.5,
                 anchor="middle"),
            text(305, 160, "v3, digest", size=11.5,
                 anchor="middle"),
            arrow([(270, 148), (258, 148)], kind="trace"),
            arrow([(239, 60), (330, 60)]),
            text(284, 52, "allow", size=11.5, weight=700,
                 anchor="middle"),
            tool(332, 40, 116, 40, "refunds.create"),
            arrow([(256, 164), (360, 196)]),
            text(252, 192, "every decision", size=11.5,
                 anchor="end", fill=MID),
            receipt(362, 180, 86, 36),
            text(405, 202, "receipt", size=11.5,
                 anchor="middle")]
    return svg(226, body)


FIGURES = {"fig-19-1-receipt-strip": lambda: receipt_strip({3}),
           "fig-19-2-action-boundary": boundary_fig}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
