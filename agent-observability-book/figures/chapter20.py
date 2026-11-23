"""Chapter 15 figures: where each attack is stopped.

Usage: python -m figures.chapter20 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import FILL, MID, PALE, box, svg, text
from policy.redteam import attacks

LAYERS = ["identity", "delegation", "policy", "tool pins",
          "sandbox", "memory", "breaker", "approval"]
WHERE = {"ASI01": "policy", "ASI02": "delegation",
         "ASI03": "delegation", "ASI04": "tool pins",
         "ASI05": "sandbox", "ASI06": "memory",
         "ASI07": "identity", "ASI08": "breaker",
         "ASI09": "approval", "ASI10": "policy"}


def matrix():
    """Figure 20.2. Each attack and the layer that stopped it."""
    rows, _ = attacks()
    x0, y0, cw, rh = 50, 70, 46, 20
    body = []
    for j, layer in enumerate(LAYERS):
        x = x0 + j * cw + cw / 2
        body.append(f'<text x="{x}" y="{y0 - 6}" '
                     f'transform="rotate(-40 {x} {y0 - 6})" '
                     f'font-family="Inter, sans-serif" '
                     f'font-size="11.5">{layer}</text>')
    for i, (threat, _, blocked, _) in enumerate(rows):
        y = y0 + i * rh
        body.append(text(4, y + 14, threat, size=11.5))
        for j, layer in enumerate(LAYERS):
            hit = WHERE[threat] == layer
            fill = (FILL if hit and blocked else
                    "#ffffff")
            kind = "3P" if hit and not blocked else None
            body.append(box(x0 + j * cw + 4, y + 3, cw - 8,
                            rh - 6, fill=fill, r=2,
                            width=0.6 if not hit else 1.4,
                            kind=kind))
    y = y0 + len(rows) * rh + 12
    body.append(box(4, y, 16, 12, fill=FILL, r=2))
    body.append(text(26, y + 11, "stopped here", size=11.5,
                     fill=MID))
    body.append(box(150, y, 16, 12, r=2, kind="3P"))
    body.append(text(172, y + 11, "gap: no control yet",
                     size=11.5, fill=MID))
    return svg(y + 24, body)


FIGURES = {"fig-20-1-receipt-strip": lambda: receipt_strip({3}),
           "fig-20-2-attack-matrix": matrix}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
