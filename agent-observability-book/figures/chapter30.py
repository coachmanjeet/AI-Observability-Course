"""Chapter 30 figures: spend during the runaway.

Usage: python -m figures.chapter30 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import FILL, MID, line, svg, text
from metering.entitlements import runaway

X0, Y0, W, H = 44, 14, 400, 150


def spend_curve():
    """Figure 30.2. Daily cost against budget, 14:00 to 14:20."""
    rt, results, _ = runaway()
    spend, pts = 4.20, []
    for i, r in enumerate(results):
        if r == "ok":
            spend += 0.015
        if i % 10 == 0:
            pts.append((X0 + W * i / len(results),
                        Y0 + H * (1 - spend / 24)))
    loop = [(X0 + W * i / 1200,
             Y0 + H * (1 - (4.2 + 0.015 * i) / 24))
            for i in (0, 1199)]
    body = [line([(X0, Y0), (X0, Y0 + H), (X0 + W, Y0 + H)]),
            line(loop, dash="4 4"),
            line([(X0, Y0 + H * (1 - 10 / 24)),
                  (X0 + W, Y0 + H * (1 - 10 / 24))], width=0.8),
            text(X0 + W, Y0 + H * (1 - 10 / 24) - 6,
                 "daily budget $10", size=11.5, anchor="end",
                 fill=MID),
            line(pts, width=2.4),
            text(X0 + W - 4, Y0 + 12, "without the switch",
                 size=11.5, anchor="end", fill=MID),
            text(X0 + 4, Y0 + H + 18, "14:00", size=11.5,
                 fill=MID),
            text(X0 + W, Y0 + H + 18, "14:20", size=11.5,
                 anchor="end", fill=MID),
            text(4, Y0 + H * (1 - 4.2 / 24) + 4, "$4.20",
                 size=11.5, fill=MID)]
    return svg(Y0 + H + 28, body)


FIGURES = {"fig-30-1-receipt-strip": lambda: receipt_strip({5}),
           "fig-30-2-runaway": spend_curve}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
