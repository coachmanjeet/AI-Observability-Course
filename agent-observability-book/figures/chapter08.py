"""Chapter 7 figures: the signed chain, and the replay loop.

Usage: python -m figures.chapter08 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, arrow, box, receipt,
                              store, svg, text, tool)


def chain():
    """Figure 8.2. One writer, a signed chain, an off-box checkpoint."""
    body = [tool(4, 40, 96, 44, "receipt writer"),
            text(52, 104, "holds the only", size=11.5,
                 anchor="middle", fill=MID),
            text(52, 118, "signing key", size=11.5, anchor="middle",
                 fill=MID)]
    for i, (x, n) in enumerate(((132, "1,168"), (240, "1,169"),
                                (348, "1,170"))):
        body += [receipt(x, 30, 96, 64, fill=PALE if i < 2 else FILL),
                 text(x + 48, 48, f"receipt {n}", size=11.5,
                      weight=600, anchor="middle"),
                 text(x + 48, 64, "hash, signature", size=11.5,
                      anchor="middle"),
                 text(x + 48, 79, "prev_hash", size=11.5, mono=True,
                      anchor="middle")]
        if i:
            body.append(arrow([(x, 74), (x - 10, 74)], kind="trace"))
    body += [arrow([(100, 62), (130, 62)]),
             text(132, 20, "append only", size=11.5, fill=MID),
             receipt(240, 140, 124, 66, fill="#ffffff"),
             text(302, 158, "checkpoint", size=11.5, weight=600,
                  anchor="middle"),
             text(302, 174, "count 1,170, head", size=11.5,
                  anchor="middle"),
             text(302, 189, "signed", size=11.5, anchor="middle"),
             arrow([(396, 100), (396, 168), (362, 168)], kind="trace"),
             store(4, 146, 110, 56, "audit copy, off box"),
             arrow([(238, 170), (116, 174)]),
             text(176, 162, "copied", size=11.5, anchor="middle",
                  fill=MID)]
    return svg(216, body)


def loop():
    """Figure 8.3. Receipt to trace to versions to rerun to diff."""
    steps = [(4, 20, "receipt"), (160, 20, "trace + links"),
             (316, 20, "records @ versions"),
             (316, 120, "rerun in sandbox"), (160, 120, "diff"),
             (4, 120, "one input changed")]
    body = []
    for x, y, label in steps:
        body.append(box(x, y, 140, 44, fill=PALE, r=6))
        body.append(text(x + 70, y + 27, label, size=12, weight=600,
                         anchor="middle"))
    body += [arrow([(144, 42), (158, 42)]),
             arrow([(300, 42), (314, 42)]),
             arrow([(386, 64), (386, 118)]),
             arrow([(316, 142), (302, 142)]),
             arrow([(160, 142), (146, 142)]),
             arrow([(74, 120), (74, 104), (386, 104), (386, 118)],
                   kind="trace"),
             text(80, 84, "evidence.trace_id", size=11.5, mono=True,
                  anchor="middle", fill=MID),
             text(230, 84, "decided_by, in_context", size=11.5,
                  mono=True, anchor="middle", fill=MID),
             text(230, 186, "reproduced, or diverged", size=11.5,
                  anchor="middle", fill=MID),
             text(74, 186, "which inputs matter", size=11.5,
                  anchor="middle", fill=MID)]
    return svg(196, body)


FIGURES = {"fig-8-1-receipt-strip": lambda: receipt_strip({4}),
           "fig-8-2-signed-chain": chain,
           "fig-8-3-replay-loop": loop}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
