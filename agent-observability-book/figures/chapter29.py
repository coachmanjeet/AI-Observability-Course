"""Chapter 22 figures: the pricing 2x2.

Usage: python -m figures.chapter29 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import FILL, MID, PALE, box, line, svg, text

# (label, predictability 0-1, value alignment 0-1)
POINTS = [("per seat", 0.90, 0.16), ("credits", 0.70, 0.36),
          ("per action", 0.46, 0.30),
          ("per conversation", 0.30, 0.08),
          ("per outcome", 0.22, 0.86),
          ("base + outcome", 0.64, 0.74)]
X0, Y0, W, H = 40, 12, 400, 200


def quad():
    """Figure 29.2. Predictable for the buyer vs. tracks value."""
    body = [box(X0, Y0, W, H, fill="none", r=0),
            line([(X0 + W / 2, Y0), (X0 + W / 2, Y0 + H)],
                 dash="3 4"),
            line([(X0, Y0 + H / 2), (X0 + W, Y0 + H / 2)],
                 dash="3 4"),
            text(X0 + W / 2, Y0 + H + 18,
                 "predictable for the buyer →", size=11.5,
                 anchor="middle", fill=MID),
            f'<text x="16" y="{Y0 + H / 2}" font-family='
            f'"Inter, sans-serif" font-size="11.5" fill="{MID}" '
            f'text-anchor="middle" transform="rotate(-90 16 '
            f'{Y0 + H / 2})">tracks value →</text>']
    for label, px, py in POINTS:
        x, y = X0 + px * W, Y0 + (1 - py) * H
        fill = FILL if label == "base + outcome" else PALE
        body.append(box(x - 6, y - 6, 12, 12, fill=fill, r=6))
        anchor = "end" if px > 0.8 else "start"
        dx = -10 if anchor == "end" else 10
        body.append(text(x + dx, y + 4, label, size=11.5,
                         anchor=anchor))
    return svg(Y0 + H + 28, body)


FIGURES = {"fig-29-1-receipt-strip": lambda: receipt_strip({5}),
           "fig-29-2-pricing-quadrant": quad}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
