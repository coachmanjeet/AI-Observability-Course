"""Chapter 12 figures: identity by attestation.

Usage: python -m figures.chapter16 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow, box,
                              gate, store, svg, text, tool)


def attestation():
    """Figure 16.2. Prove what you are, get a short-lived ID."""
    body = [agent(4, 70, 80, 40, "Speedy"),
            box(4, 126, 80, 52, fill=PALE, r=4),
            text(10, 144, "namespace", size=11.5),
            text(10, 158, "service acct", size=11.5),
            text(10, 172, "image digest", size=11.5),
            arrow([(84, 90), (124, 90)]),
            text(104, 82, "1", size=11.5, weight=700,
                 anchor="middle"),
            tool(126, 62, 112, 56, "identity issuer"),
            store(140, 140, 84, 46, "entries +", fill=PALE),
            text(182, 200, "registry state", size=11.5,
                 anchor="middle", fill=MID),
            arrow([(182, 120), (182, 138)], kind="trace"),
            arrow([(238, 90), (276, 90)]),
            text(256, 82, "2", size=11.5, weight=700,
                 anchor="middle"),
            box(278, 70, 74, 40, fill=FILL, r=4),
            text(315, 87, "SVID", size=12, weight=700,
                 anchor="middle"),
            text(315, 102, "5 min, 1 aud", size=11.5,
                 anchor="middle"),
            arrow([(352, 90), (380, 90)]),
            text(368, 82, "3", size=11.5, weight=700,
                 anchor="middle"),
            gate(412, 90, 31),
            text(412, 94, "gateway", size=11.5, anchor="middle"),
            text(412, 140, "checks issuer,", size=11.5,
                 anchor="middle", fill=MID),
            text(412, 154, "audience, expiry", size=11.5,
                 anchor="middle", fill=MID)]
    return svg(212, body)


FIGURES = {"fig-16-1-receipt-strip": lambda: receipt_strip({0}),
           "fig-16-2-attestation": attestation}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
