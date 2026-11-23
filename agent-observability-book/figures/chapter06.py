"""Chapter 5 figures: one action traced back to the versioned records
it rested on, and decisions placed against the policy version in view.

Usage: python -m figures.chapter06 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, arrow, box, line, store,
                              svg, text, tool)

LINK = "5 3"


def decision_graph():
    """Figure 6.2. The $40 refund, back to the records it rested on."""
    body = [
        tool(150, 10, 160, 46, ""),
        text(230, 29, "refunds.create", size=12, weight=600,
             anchor="middle"),
        text(230, 46, "order:ord_5521", size=11.5, mono=True,
             anchor="middle"),
        text(318, 37, "→ refund:rf_9931", size=11.5, mono=True),
        arrow([(230, 56), (230, 92)], kind="trace", dash=LINK),
        text(238, 79, "decided_by", size=11.5, mono=True),
        box(140, 94, 180, 46, fill=PALE),
        text(230, 113, "chat pronto-mock-1", size=12, weight=600,
             anchor="middle"),
        text(230, 130, "resp_03, ends 02:07:12", size=11.5,
             anchor="middle"),
    ]
    reads = [("orders.get", "02:06:41", "order:ord_5521", "etag-9f2c",
              "system:orders", "confidential"),
             ("policy.lookup", "02:06:45", "policy:refunds",
              "2026-10-01", "team:finance", "internal"),
             ("photos.verify", "02:06:52", "photo:photo_7c1",
              "etag-41c7", "system:photos", "confidential")]
    for i, (name, when, sid, version, owner, level) in enumerate(reads):
        x = 6 + i * 152
        cx = x + 70
        body += [
            arrow([(230, 140), (230, 158), (cx, 158), (cx, 190)],
                  kind="trace", dash=LINK),
            tool(x, 192, 140, 44, ""),
            text(cx, 210, name, size=12, weight=600, anchor="middle"),
            text(cx, 227, f"read at {when}", size=11.5,
                 anchor="middle"),
            arrow([(cx, 236), (cx, 262)], kind="trace"),
            store(x, 264, 140, 54, ""),
            text(cx, 290, sid, size=11.5, mono=True, anchor="middle"),
            text(cx, 306, version, size=11.5, mono=True,
                 anchor="middle"),
            text(cx, 336, owner, size=11.5, anchor="middle", fill=MID),
            text(cx, 351, level, size=11.5, anchor="middle", fill=MID),
        ]
    body += [text(120, 151, "in_context", size=11.5, mono=True,
                  anchor="middle"),
             text(4, 378, "From the span: source ID and version. From "
                  "the catalog: authority", size=11.5),
             text(4, 393, "and sensitivity, in gray.", size=11.5),
             arrow([(4, 416), (50, 416)], kind="trace", dash=LINK),
             text(56, 420, "span link (pronto.link)", size=11.5),
             arrow([(246, 416), (292, 416)], kind="trace"),
             text(298, 420, "read: on the tool span", size=11.5)]
    return svg(428, body)


def versions_in_view():
    """Figure 6.3. Three decisions, two versions of the refund policy."""
    body = [text(4, 18, "policy:refunds", size=12, weight=700, mono=True),
            box(16, 30, 274, 30, fill=PALE),
            text(153, 50, "version 2026-10-01", size=11.5, mono=True,
                 anchor="middle"),
            box(290, 30, 164, 30, fill=FILL),
            text(372, 50, "version 2026-11-16", size=11.5, mono=True,
                 anchor="middle"),
            line([(290, 24), (290, 140)], width=1.0, dash="2 3"),
            text(454, 18, "Monday: finance publishes", size=11.5,
                 anchor="end", fill=MID),
            line([(16, 140), (454, 140)], width=1.2)]
    for x, when, what, ref in [(80, "Sat 02:07", "refund", "rf_9931"),
                               (200, "Sat 02:20", "escalation",
                                "case_221"),
                               (380, "Mon 10:14", "refund", "rf_9932")]:
        body += [line([(x, 60), (x, 132)], width=1.1, dash=LINK),
                 f'<circle cx="{x}" cy="140" r="6" fill="#000000"/>',
                 text(x, 162, when, size=11.5, weight=600,
                      anchor="middle"),
                 text(x, 177, what, size=11.5, anchor="middle"),
                 text(x, 192, ref, size=11.5, mono=True,
                      anchor="middle")]
    body.append(text(454, 214, "Time, not to scale", size=11.5,
                     italic=True, anchor="end", fill=MID))
    return svg(222, body)


FIGURES = {"fig-6-1-receipt-strip": lambda: receipt_strip({2}),
           "fig-6-2-decision-graph": decision_graph,
           "fig-6-3-versions-in-view": versions_in_view}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
