"""Chapter 3 figures: the framework map, reference architecture,
maturity ladder and the book's notation legend.

Usage: python -m figures.chapter03 OUT_DIR
"""
import json
import pathlib
import sys

from figures.notation import (FILL, MID, PALE, WIDTH, agent, arrow, badge,
                              boundary, box, gate, line, receipt, store,
                              svg, text, tool)
from figures.chapter02 import receipt_strip
from maturity.assess import NAMES, score

PILLARS = [
    ("Discover", "Which agents run,\nas whom?",
     "Discovery\nRegistry\nAgent identity\nDelegation",
     "Who acted?\nFor whom?", "Part IV"),
    ("Govern", "What may they\nknow and do?",
     "Trusted context\nLeast privilege\nPolicy gates\nApprovals",
     "Knowing what?\nUnder which rule?", "Parts III, V"),
    ("Observe", "What did they do,\nat what cost?",
     "Traces\nAudit trails\nMetering\nCompliance",
     "Doing what?\nAt what cost?\nWhere?", "Parts II, VII, VIII"),
]


def discover_govern_observe(here=None):
    """Figure 3.2. The recurring part-opener map. here marks a pillar."""
    body = [f'<polygon points="4,62 230,6 456,62" fill="{PALE}" '
            'stroke="#000" stroke-width="1.4"/>',
            text(230, 40, "AI Control Tower", size=13, weight=700,
                 anchor="middle"),
            text(230, 56, "runs all three, for 1P and 3P agents (Part VI)",
                 size=11.5, anchor="middle")]
    for i, (name, asks, covers, questions, parts) in enumerate(PILLARS):
        x, w = 14 + i * 147, 138
        on = here == name
        body += [box(x, 72, w, 196, fill=FILL if on else "#ffffff",
                     width=2.2 if on else 1.4),
                 text(x + w / 2, 92, name, size=14, weight=700,
                      anchor="middle"),
                 text(x + w / 2, 110, asks, size=11.5, italic=True,
                      anchor="middle"),
                 line([(x + 12, 136), (x + w - 12, 136)], width=0.9),
                 text(x + w / 2, 154, covers, size=11.5, anchor="middle"),
                 line([(x + 12, 210), (x + w - 12, 210)], width=0.9),
                 text(x + w / 2, 228, questions, size=11.5, weight=600,
                      anchor="middle"),
                 text(x + w / 2, 284, parts, size=11.5, anchor="middle",
                      fill=MID)]
        if on:
            body.append(text(x + w / 2, 66, "you are here", size=11.5,
                             weight=700, anchor="middle"))
    body += [receipt(4, 294, 452, 50, width=2.0),
             text(230, 314, "Agent Receipt", size=13, weight=700,
                  anchor="middle"),
             text(230, 330, "one record per consequential action, seven "
                  "answers (Ch 2)", size=11.5, anchor="middle")]
    return svg(352, body)


def reference_architecture():
    """Figure 3.3. Data plane, control plane, enforcement points."""
    body = [box(4, 6, 452, 60, width=2.0),
            text(14, 25, "AI Control Tower (Ch 24)", size=12.5, weight=700)]
    for i, item in enumerate(["Fleet inventory", "Receipt explorer",
                              "Budgets", "Kill switch"]):
        body += [box(14 + i * 110, 34, 102, 24),
                 text(65 + i * 110, 50, item, size=11.5, anchor="middle")]
    body += [arrow([(230, 86), (230, 70)], kind="trace", both=True),
             text(240, 82, "sees every agent; can stop any of them",
                  size=11.5, italic=True),
             box(4, 90, 452, 122),
             text(14, 108, "Control plane: decides and records",
                  size=12.5, weight=700)]
    planes = [("store", "Registry\nCh 15"), ("box", "Identity\nCh 16, 17"),
              ("box", "Policy admin\nCh 19, 21"),
              ("store", "Context catalog\nCh 9–13"),
              ("store", "Traces, receipts\nCh 4–8"),
              ("box", "Metering\nCh 27–30")]
    for i, (shape, label) in enumerate(planes):
        x, y = 14 + (i % 3) * 148, 116 + (i // 3) * 46
        if shape == "store":
            body.append(store(x, y, 136, 40, label, size=11.5))
        else:
            body += [box(x, y + 2, 136, 36),
                     text(x + 68, y + 17, label, size=11.5,
                          anchor="middle")]
    body += [arrow([(60, 214), (60, 238)]),
             text(68, 230, "policy, identity, context", size=11.5,
                  italic=True),
             arrow([(400, 238), (400, 214)], kind="trace"),
             text(392, 230, "traces, receipts, usage", size=11.5,
                  italic=True, anchor="end"),
             box(4, 242, 452, 202),
             text(14, 260, "Data plane: acts", size=12.5, weight=700),
             agent(14, 272, 110, 32, "Speedy", kind="1P", size=11.5),
             boundary(10, 314, 120, 62, "PayCo"),
             agent(14, 334, 110, 32, "Ledger", kind="3P", size=11.5),
             agent(14, 394, 110, 32, "Night Owl", kind="shadow",
                   size=11.5),
             gate(222, 330, 36, "Gateway"),
             text(222, 380, "MCP, A2A, API", size=11.5, anchor="middle"),
             receipt(205, 258, 34, 30, fill=PALE),
             text(246, 278, "receipt", size=11.5, italic=True),
             arrow([(124, 288), (196, 318)]),
             arrow([(130, 350), (186, 334)]),
             tool(326, 274, 120, 30, "Orders MCP", size=11.5),
             tool(326, 326, 120, 30, "Refunds MCP", size=11.5),
             tool(326, 396, 120, 30, "Payments API", size=11.5),
             arrow([(258, 330), (324, 292)]),
             arrow([(258, 334), (324, 340)]),
             arrow([(124, 411), (324, 411)]),
             text(222, 404, "no gate in the path", size=11.5,
                  italic=True, anchor="middle")]
    return svg(450, body)


def maturity_ladder(fleet_path):
    """Figure 3.4. Pronto's agents on the five rungs, from fleet.json."""
    fleet = json.loads(pathlib.Path(fleet_path).read_text())
    rungs = {level: [] for level in NAMES}
    for a in fleet["agents"]:
        rungs[score(a)[0]].append(a)
    needs = {5: "an R4 receipt for\nevery action",
             4: "rules outside the model,\nevery action traced",
             3: "its own identity,\nscoped access",
             2: "in a registry,\nwith an owner",
             1: "running, on\nno one's list"}
    body, pitch = [], 64
    for level in range(5, 0, -1):
        y = 6 + (5 - level) * pitch
        body += [box(4, y, 452, pitch - 6, fill=PALE if level == 1
                     else "#ffffff"),
                 badge(22, y + 29, f"L{level}", size=11.5),
                 text(42, y + 19, NAMES[level], size=12, weight=700),
                 text(42, y + 34, needs[level], size=11.5, fill=MID)]
        for j, a in enumerate(rungs[level]):
            body.append(agent(204 + j * 84, y + 14, 78, 30, a["name"],
                              kind=a["kind"], size=11.5))
        if not rungs[level]:
            body.append(text(206, y + 34, "no agent yet", size=11.5,
                             italic=True))
    y1 = 6 + 4 * pitch
    body += [text(296, y1 + 25, "Estate level: L1,", size=11.5,
                  weight=700),
             text(296, y1 + 40, "set by its weakest agent", size=11.5)]
    return svg(6 + 5 * pitch, body)


def legend():
    """Figure 3.5. The notation used in every figure in the book."""
    cells = [
        (lambda x, y: agent(x, y, 104, 32, "Speedy", kind="1P",
                            size=11.5), "First-party agent"),
        (lambda x, y: agent(x, y, 104, 32, "Ledger", kind="3P",
                            size=11.5), "Third-party agent"),
        (lambda x, y: agent(x, y, 104, 32, "Night Owl", kind="shadow",
                            size=11.5), "Shadow agent"),
        (lambda x, y: tool(x, y + 4, 104, 28, "refunds.create",
                           size=11.5), "Tool, MCP server or API"),
        (lambda x, y: gate(x + 52, y + 16, 18), "Policy gate"),
        (lambda x, y: store(x, y, 104, 34, "Registry", size=11.5),
         "Data store"),
        (lambda x, y: receipt(x + 30, y, 44, 34), "Agent Receipt"),
        (lambda x, y: boundary(x, y - 2, 104, 38, "PayCo"),
         "Trust boundary"),
        (lambda x, y: badge(x + 52, y + 16, "19"), "Chapter or callout"),
        (lambda x, y: arrow([(x, y + 16), (x + 104, y + 16)]),
         "Call"),
        (lambda x, y: arrow([(x, y + 16), (x + 104, y + 16)],
                            kind="trace"), "Trace context, telemetry"),
        (lambda x, y: box(x, y, 104, 32, fill=FILL, width=2.2),
         "This chapter's focus"),
    ]
    body = []
    for i, (draw, label) in enumerate(cells):
        cx = 6 + (i % 3) * 152
        cy = 12 + (i // 3) * 72
        body += [draw(cx + 20, cy), text(cx + 72, cy + 54, label, size=11.5,
                                         anchor="middle")]
    return svg(12 + 4 * 72, body)


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    here = pathlib.Path(__file__).parent.parent
    figures = {
        "fig-3-1-receipt-strip": receipt_strip(highlight={0, 3}),
        "fig-3-2-discover-govern-observe": discover_govern_observe(),
        "fig-3-3-reference-architecture": reference_architecture(),
        "fig-3-4-maturity-ladder": maturity_ladder(
            here / "maturity" / "fleet.json"),
        "fig-3-5-notation-legend": legend(),
    }
    for name, content in figures.items():
        (out / f"{name}.svg").write_text(content, encoding="utf-8")
        print("wrote", out / f"{name}.svg")
