"""Chapter 26 figures: the full receipt and the 90-day plan.

Usage: python -m figures.chapter34 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (DASH, FILL, MID, PALE, arrow, box,
                              line, svg, text)

X0, X1 = 74, 448


def day(d):
    return X0 + (X1 - X0) * d / 90


def mark(d, y, label, above=True, anchor="middle"):
    ty = y - 10 if above else y + 22
    return [line([(day(d), y - 5), (day(d), y + 5)], width=2.2),
            text(day(d), ty, label, size=11.5, anchor=anchor)]


def rollout():
    """Figure 34.2. Ship four agents, hold two, re-review."""
    body = [text(4, 52, "enforce", size=11.5, weight=700),
            text(4, 122, "observe", size=11.5, weight=700),
            text(4, 186, "evidence", size=11.5, weight=700),
            box(day(0), 40, day(14) - day(0), 16, fill=PALE,
                kind="boundary"),
            box(day(14), 40, day(90) - day(14), 16, fill=FILL),
            text(day(52), 74, "Speedy, Pick, Route, Coder",
                 size=11.5, anchor="middle"),
            text(day(7), 74, "10%", size=11.5, anchor="middle",
                 fill=MID),
            box(day(0), 110, day(90) - day(0), 16, fill="#ffffff",
                kind="boundary"),
            text(day(12), 144, "Ledger, Promo", size=11.5,
                 anchor="middle"),
            arrow([(day(30), 108), (day(30), 60)]),
            text(day(30) + 4, 96, "Ledger R4", size=11.5,
                 fill=MID),
            line([(X0, 182), (X1, 182)])]
    body += mark(30, 182, "pack")
    body += mark(45, 182, "A.5.2, model-b", above=False)
    body += mark(59, 182, "Promo traces")
    body += mark(90, 182, "re-review", above=False,
                 anchor="end")
    for d, label in ((0, "Jan 10"), (30, "Feb 9"),
                     (60, "Mar 10"), (90, "Apr 9")):
        anchor = "start" if d == 0 else "end" if d == 90 \
            else "middle"
        body.append(text(day(d), 234, label, size=11.5,
                         anchor=anchor, fill=MID))
    return svg(244, body)


FIGURES = {"fig-34-1-receipt-strip":
           lambda: receipt_strip(set(range(7))),
           "fig-34-2-rollout": rollout}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
