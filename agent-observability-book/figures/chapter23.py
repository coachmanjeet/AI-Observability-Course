"""Chapter 23 figures: one workflow across a night.

Usage: python -m figures.chapter23 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, arrow, box, line,
                              receipt, svg, text)

# step, time, label, x position (overnight gap is not to scale)
STEPS = [("vision", "Mon 14:02", "photo", 50),
         ("voice", "14:05", "customer", 120),
         ("timer", "14:06", "wait", 190),
         ("voice", "Tue 08:00", "driver", 330),
         ("credit", "08:41", "$5.99", 410)]


def timeline():
    """Figure 23.2. Five steps, two crashes, three receipts."""
    body = [line([(30, 70), (236, 70)]),
            line([(236, 70), (284, 70)], dash="3 4"),
            line([(284, 70), (440, 70)]),
            text(260, 62, "overnight", size=11.5, fill=MID,
                 anchor="middle")]
    for step, at, label, cx in STEPS:
        body.append(box(cx - 4, 64, 8, 12, fill=FILL))
        body.append(text(cx, 30, step, size=11.5, weight=600,
                         anchor="middle"))
        body.append(text(cx, 44, label, size=11.5, fill=MID,
                         anchor="middle"))
        body.append(text(cx, 94, at, size=11.5, fill=MID,
                         anchor="middle"))
    for cx, label in ((260, "02:13 crash"),
                      (436, "crash")):
        body.append(text(cx, 114, "×", size=14, weight=700,
                         anchor="middle"))
        body.append(text(cx, 128, label, size=11.5, fill=MID,
                         anchor="middle"))
    y = 142
    for i, label in enumerate(["voice", "voice", "credit"]):
        rx = 40 + i * 140
        body.append(receipt(rx, y, 96, 34))
        body.append(text(rx + 48, y + 21, f"receipt: {label}",
                         size=11.5, anchor="middle"))
        if i:
            body.append(arrow([(rx, y + 14), (rx - 42, y + 14)],
                              kind="trace"))
    body.append(text(40, y + 54, "each receipt points to the one "
                     "before: parent_receipt_id", size=11.5,
                     fill=MID))
    return svg(y + 64, body)


FIGURES = {"fig-23-1-receipt-strip": lambda: receipt_strip({4}),
           "fig-23-2-workflow": timeline}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
