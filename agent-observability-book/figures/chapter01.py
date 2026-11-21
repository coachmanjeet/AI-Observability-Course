"""Chapter 1 figures: the night of Nov 14, 2026, and the seven
questions every chapter answers.

Usage: python -m figures.chapter01 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, agent, arrow, box, gate, line,
                              store, svg, text)
from incident.replay import payments

X0, X1 = 104, 352          # 2:00 a.m. to 2:15 a.m.


def at(stamp):
    """x position of an HH:MM:SS time between 2:00 and 2:15."""
    h, m, s = (int(p) for p in stamp.split(":"))
    minutes = (h - 2) * 60 + m + s / 60
    return X0 + (X1 - X0) * minutes / 15


def the_night():
    """Figure 1.1. Two refunds, one gate, one trace."""
    log = {p["refund"]: p for p in payments()}
    speedy = at(log["rf_9931"]["time"][11:19])
    owl = at(log["rf_9934"]["time"][11:19])
    body = [text(4, 16, "Saturday, Nov 14, 2026", size=12, weight=700),
            agent(4, 40, 88, 36, "Speedy", kind="1P"),
            agent(4, 112, 88, 36, "Night Owl", kind="shadow"),
            store(362, 52, 94, 84, "payments API", fill=FILL,
                  size=11.5)]
    # Speedy: a 39-second turn with a trace, through the $50 check
    start = speedy - (X1 - X0) * 33 / 900
    body += [line([(92, 58), (start, 58)], width=1.0),
             box(start, 51, speedy - start, 14, fill=FILL),
             text(start - 4, 46, "trace, 9 spans", size=11.5,
                  anchor="end", fill=MID),
             gate(speedy + 14, 56, 9),
             text(speedy + 14, 82, "$50 check", size=11.5,
                  anchor="middle", fill=MID),
             arrow([(speedy + 23, 56), (360, 76)]),
             text(300, 50, "$40", size=12, weight=700,
                  anchor="middle")]
    # Night Owl: straight to the API, no trace, no gate
    body += [arrow([(92, 130), (owl, 130), (360, 112)]),
             text(owl - 10, 146, "no trace, no gate", size=11.5,
                  anchor="end", fill=MID),
             text(owl + 14, 108, "$85", size=12, weight=700,
                  anchor="middle")]
    # time axis
    body.append(line([(X0, 172), (X1, 172)], width=1.0))
    for minute in (0, 5, 10, 15):
        x = X0 + (X1 - X0) * minute / 15
        body += [line([(x, 168), (x, 176)], width=1.0),
                 text(x, 190, f"2:{minute:02d}", size=11.5,
                      anchor="middle")]
    for x, label in ((speedy, "02:07:13"), (owl, "02:11:52")):
        body.append(f'<circle cx="{x:.1f}" cy="172" r="4" '
                    'fill="#000000"/>')
        body.append(text(x, 206, label, size=11.5, mono=True,
                         anchor="middle"))
    body.append(text(4, 232, "Monday, 9:12 a.m.: which agent? "
                     "for whom? under which rule?", size=11.5,
                     weight=600))
    return svg(242, body)


FIGURES = {"fig-1-1-the-night": the_night,
           "fig-1-2-receipt-strip": receipt_strip}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
