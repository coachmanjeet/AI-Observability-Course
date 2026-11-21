"""Chapter 28 figures: from span to invoice line.

Usage: python -m figures.chapter28 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, arrow, box,
                              receipt, store, svg, text)

STAGES = [("agent span", "conv_6f43…", "#ffffff"),
          ("usage event", "pending, key", PALE),
          ("outcome", "record, day 7", "#ffffff"),
          ("billed event", "same key, 1", FILL),
          ("invoice line", "$0.40", PALE)]


def pipeline():
    """Figure 28.2. One key follows the work to the invoice."""
    body = []
    for i, (name, note, fill) in enumerate(STAGES):
        x = 4 + i * 91
        body.append(box(x, 20, 78, 48, fill=fill, r=5))
        body.append(text(x + 39, 40, name, size=11.5,
                         weight=600, anchor="middle"))
        body.append(text(x + 39, 57, note, size=11.5,
                         anchor="middle", fill=MID))
        if i < len(STAGES) - 1:
            body.append(arrow([(x + 78, 44), (x + 91, 44)]))
    body.append(text(4, 96, "duplicate from a retry: same key, "
                     "dropped", size=11.5, fill=MID))
    body.append(text(4, 114, "outcome after the close: billed "
                     "next month, original date", size=11.5,
                     fill=MID))
    body.append(text(4, 132, "review reverses it: credit, key "
                     "+ ':credit'", size=11.5, fill=MID))
    return svg(142, body)


FIGURES = {"fig-28-1-receipt-strip": lambda: receipt_strip({5}),
           "fig-28-2-usage-pipeline": pipeline}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
