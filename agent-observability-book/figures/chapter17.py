"""Chapter 12 figures: delegation by token exchange.

Usage: python -m figures.chapter17 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow, box,
                              gate, store, svg, text, tool)


def exchange():
    """Figure 17.2. Two tokens in, one narrower token out."""
    body = [box(4, 20, 92, 40, r=20),
            text(50, 44, "customer", size=12, anchor="middle"),
            arrow([(50, 60), (50, 96)]),
            text(56, 82, "session", size=11.5),
            agent(4, 98, 92, 40, "Speedy"),
            box(4, 150, 92, 28, fill=PALE, r=4),
            text(50, 168, "SVID (Ch 12)", size=11.5,
                 anchor="middle"),
            arrow([(96, 118), (144, 118)]),
            text(120, 110, "1", size=11.5, weight=700,
                 anchor="middle"),
            tool(146, 92, 118, 52, "token exchange"),
            store(146, 18, 54, 44, "consent", fill=PALE),
            store(210, 18, 54, 44, "registry", fill=PALE),
            arrow([(173, 62), (190, 90)], kind="trace"),
            arrow([(237, 62), (220, 90)], kind="trace"),
            arrow([(264, 118), (296, 118)]),
            text(280, 110, "2", size=11.5, weight=700,
                 anchor="middle"),
            box(298, 84, 76, 68, fill=FILL, r=4),
            text(336, 100, "sub cust", size=11.5,
                 anchor="middle"),
            text(336, 114, "act Speedy", size=11.5,
                 anchor="middle"),
            text(336, 128, "2 scopes", size=11.5,
                 anchor="middle"),
            text(336, 142, "5 min", size=11.5, anchor="middle"),
            arrow([(374, 118), (396, 118)]),
            text(385, 110, "3", size=11.5, weight=700,
                 anchor="middle"),
            gate(428, 118, 31),
            text(428, 122, "gateway", size=11.5,
                 anchor="middle"),
            text(410, 168, "scope, owner,", size=11.5,
                 anchor="middle", fill=MID),
            text(410, 182, "limit, expiry", size=11.5,
                 anchor="middle", fill=MID),
            text(205, 168, "checks capability", size=11.5,
                 anchor="middle", fill=MID),
            text(205, 182, "and consent", size=11.5,
                 anchor="middle", fill=MID)]
    return svg(196, body)


FIGURES = {"fig-17-1-receipt-strip": lambda: receipt_strip({1}),
           "fig-17-2-token-exchange": exchange}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
