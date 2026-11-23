"""Chapter 11 figures: seven sources, one inventory.

Usage: python -m figures.chapter14 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, arrow, box, gate,
                              receipt, svg, text)

SOURCES = ["cloud consoles", "MCP gateway", "API logs",
           "identity provider", "endpoints", "network egress",
           "vendor reports"]


def seven_sources():
    """Figure 14.2. Evidence, joined on three keys, diffed."""
    body = []
    for i, name in enumerate(SOURCES):
        y = 8 + i * 30
        body += [box(4, y, 126, 24, fill=PALE, r=4),
                 text(12, y + 17, name, size=11.5),
                 arrow([(130, y + 12), (176, 108)], kind="trace")]
    body += [box(178, 78, 112, 60, fill=FILL, r=6),
             text(234, 100, "join on", size=11.5, weight=600,
                  anchor="middle"),
             text(234, 116, "agent ID,", size=11.5, anchor="middle"),
             text(234, 131, "credential, host", size=11.5,
                  anchor="middle"),
             arrow([(290, 108), (318, 108)]),
             gate(346, 108, 26),
             text(346, 112, "diff", size=11.5, weight=600,
                  anchor="middle"),
             text(346, 152, "vs inventory", size=11.5,
                  anchor="middle", fill=MID),
             arrow([(372, 108), (390, 108)]),
             receipt(392, 70, 64, 76, fill="#ffffff"),
             text(424, 98, "draft", size=11.5, weight=600,
                   anchor="middle"),
             text(424, 114, "records", size=11.5, anchor="middle")]
    return svg(222, body)


FIGURES = {"fig-14-1-receipt-strip": lambda: receipt_strip({0}),
           "fig-14-2-seven-sources": seven_sources}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
