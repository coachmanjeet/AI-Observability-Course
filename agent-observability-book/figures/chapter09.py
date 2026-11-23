"""Chapter 8 figures: the receipt strip, and Tuesday's seven
candidates through the catalog's five checks, drawn from the lab.

Usage: python -m figures.chapter09 OUT_DIR
"""
import pathlib
import sys

from context import supply
from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow, box,
                              gate, line, store, svg, text)

CHECKS = ["listed", "owner", "fresh", "intact", "origin"]
FAILS = {"not in the catalog": 0, "can't state": 1,
         "superseded": 2, "digest": 3, "instructions": 4}


def failed_at(reason):
    """Index of the check a rejection failed, or None."""
    for key, i in FAILS.items():
        if key in reason:
            return i
    return None


def mark(cx, cy, state):
    if state == "pass":
        return (f'<circle cx="{cx}" cy="{cy}" r="5" '
                'fill="#000000"/>')
    if state == "fail":
        return "\n".join([line([(cx - 5, cy - 5), (cx + 5, cy + 5)],
                               width=2.2),
                          line([(cx - 5, cy + 5), (cx + 5, cy - 5)],
                               width=2.2)])
    return line([(cx - 5, cy), (cx + 5, cy)], width=1.4,
                color=FILL)


def checks():
    """Figure 9.2. Seven candidates, five checks, three admitted."""
    rows, stamps = supply.retrieve()
    body = [store(4, 6, 104, 50, "systems of\nrecord", size=11.5),
            arrow([(108, 31), (176, 31)], kind="call"),
            gate(208, 31, 26, "catalog", size=11.5),
            arrow([(234, 31), (300, 31)], kind="call"),
            agent(302, 10, 154, 42, "Speedy's context", size=11.5),
            text(142, 24, "candidates", size=11.5, anchor="middle",
                 italic=True),
            text(267, 24, "stamped", size=11.5, anchor="middle",
                 italic=True)]
    top, col0, step = 96, 196, 44
    for j, name in enumerate(CHECKS):
        body.append(text(col0 + j * step, top - 10, name, size=11.5,
                         weight=600, anchor="middle"))
    body.append(text(4, top - 10, "candidate", size=11.5,
                     weight=600))
    body.append(text(456, top - 10, "verdict", size=11.5,
                     weight=600, anchor="end"))
    for i, (c, verdict, reason) in enumerate(rows):
        y = top + i * 34
        if verdict == "admit":
            body.append(box(0, y - 4, 460, 32, fill=PALE))
        body += [text(4, y + 10, c["id"], size=11.5, mono=True),
                 text(4, y + 24, f"@ {c['version']}, {c['via']}",
                      size=11.5, fill=MID)]
        stop = failed_at(reason) if verdict == "reject" else None
        for j in range(len(CHECKS)):
            state = ("pass" if stop is None or j < stop else
                     "fail" if j == stop else "skip")
            body.append(mark(col0 + j * step, y + 13, state))
        body.append(text(456, y + 17, verdict, size=12,
                         weight=700 if verdict == "admit" else 400,
                         anchor="end"))
    y = top + len(rows) * 34 + 12
    body += [mark(10, y, "pass"),
             text(22, y + 4, "passed", size=11.5),
             mark(90, y, "fail"), text(102, y + 4, "failed",
                                       size=11.5),
             mark(166, y, "skip"),
             text(178, y + 4, "not reached", size=11.5),
             text(456, y + 4, f"{len(stamps)} of {len(rows)} "
                  "admitted", size=11.5, anchor="end",
                  weight=600)]
    return svg(y + 14, body)


FIGURES = {"fig-9-1-receipt-strip": lambda: receipt_strip({2}),
           "fig-9-2-five-checks": checks}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
