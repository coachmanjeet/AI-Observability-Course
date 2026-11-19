"""Chapter 5 figures: one conversation across four services, continue
or link, and receipts linked across a company boundary.

Usage: python -m figures.chapter05 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow, box,
                              boundary, line, receipt, svg, text, tool)

LINK = "5 3"
TRACE_FILL = {"4bf9": "#ffffff", "3f1a": PALE, "c4e8": FILL,
              "7d2e": "#ffffff"}


def block(x, y, w, h, lines, trace_id, kind="1P"):
    """A span group, labeled with its trace so it reads without fill."""
    body = [agent(x, y, w, h, "", kind=kind, fill=TRACE_FILL[trace_id])]
    for i, s in enumerate(lines):
        body.append(text(x + w / 2, y + 17 + i * 15, s, size=11.5,
                         weight=600 if i == 0 else 400,
                         anchor="middle"))
    body.append(text(x + w / 2, y + h - 9, f"trace {trace_id}…",
                     size=11.5, anchor="middle", mono=True))
    return "\n".join(body)


def span(x, y, w, h, name, trace_id):
    """A server span: the tool box notation, with its trace."""
    return "\n".join([
        tool(x, y, w, h, ""),
        text(x + w / 2, y + 17, name, size=11.5, anchor="middle"),
        text(x + w / 2, y + h - 9, f"trace {trace_id}…", size=11.5,
             mono=True, anchor="middle")])


def swimlane():
    """Figure 5.2. Saturday's conversation, four services, four traces."""
    sp, mcp, nt, lg = (4, 90), (136, 96), (244, 88), (352, 100)
    mid = {k: x + w / 2 for k, (x, w) in
           {"sp": sp, "mcp": mcp, "nt": nt, "lg": lg}.items()}
    body = [boundary(342, 4, 116, 412, "PayCo")]
    for name, key in [("Speedy", "sp"), ("MCP server", "mcp"),
                      ("Notifier", "nt"), ("Ledger", "lg")]:
        body += [text(mid[key], 32, name, size=12, weight=700,
                      anchor="middle"),
                 line([(mid[key], 40), (mid[key], 412)], width=0.6,
                      dash="2 4", color=MID)]
    meta_x = sp[0] + sp[1] + 22
    body += [
        # Turn 1: the refund. MCP calls continue Speedy's trace.
        block(sp[0], 50, sp[1], 140, ["Turn 1", "refund"], "4bf9"),
        span(mcp[0], 56, mcp[1], 44, "orders.get", "4bf9"),
        span(mcp[0], 112, mcp[1], 44, "refunds.create", "4bf9"),
        arrow([(sp[0] + sp[1], 78), (mcp[0] - 2, 78)], kind="trace"),
        text(meta_x, 72, "_meta", size=11.5, mono=True,
             anchor="middle"),
        arrow([(sp[0] + sp[1], 134), (mcp[0] - 2, 134)], kind="trace"),
        text(meta_x, 128, "_meta", size=11.5, mono=True,
             anchor="middle"),
        # The queue: delivered later, as a new trace with a link.
        arrow([(sp[0] + sp[1], 178), (mid["nt"], 178),
               (mid["nt"], 206)], kind="trace", dash=LINK),
        text(mcp[0] - 6, 172, "message headers, link", size=11.5,
             italic=True),
        block(nt[0], 208, nt[1], 64, ["process", "2 min later"],
              "7d2e"),
        # Turn 2: the dispute. PayCo starts its own trace and links.
        block(sp[0], 290, sp[1], 70, ["Turn 2", "dispute"], "3f1a"),
        text(mcp[0] - 6, 306, "traceparent header, link", size=11.5,
             italic=True),
        arrow([(sp[0] + sp[1], 312), (lg[0] - 2, 312)], kind="trace",
              dash=LINK),
        block(lg[0], 290, lg[1], 64, ["Ledger"], "c4e8", kind="3P"),
        # Ledger reads the order through Pronto's MCP server.
        span(mcp[0], 362, mcp[1], 44, "orders.get", "c4e8"),
        arrow([(mid["lg"], 354), (mid["lg"], 384),
               (mcp[0] + mcp[1] + 2, 384)], kind="trace"),
        text(mid["nt"], 378, "_meta", size=11.5, mono=True,
             anchor="middle"),
    ]
    y = 436
    body += [arrow([(4, y), (50, y)], kind="trace"),
             text(56, y + 4, "parent: the trace continues", size=11.5),
             arrow([(242, y), (288, y)], kind="trace", dash=LINK),
             text(294, y + 4, "link: a new trace", size=11.5)]
    return svg(446, body)


def continue_or_link():
    """Figure 5.3. Two ways to cross a boundary."""
    body = []
    for i, (title, note1, note2, linked) in enumerate([
            ("Continue", "Inside your trust boundary,", "seconds apart",
             False),
            ("Link", "Across a company, or after", "a long wait", True)]):
        x0 = 4 + i * 232
        body += [text(x0 + 110, 16, title, size=13, weight=700,
                      anchor="middle"),
                 box(x0, 26, 220, 150, fill="none", width=0.9)]
        body += [agent(x0 + 14, 40, 92, 30, "caller span", size=11.5),
                 text(x0 + 60, 86, "trace A", size=11.5, mono=True,
                      anchor="middle")]
        if linked:
            body += [agent(x0 + 114, 104, 92, 30, "new root", size=11.5),
                     text(x0 + 160, 150, "trace B", size=11.5, mono=True,
                          anchor="middle"),
                     arrow([(x0 + 60, 92), (x0 + 60, 119),
                            (x0 + 112, 119)], kind="trace", dash=LINK),
                     text(x0 + 66, 113, "link", size=11.5, italic=True)]
        else:
            body += [agent(x0 + 114, 104, 92, 30, "child span",
                           size=11.5),
                     text(x0 + 160, 150, "trace A", size=11.5, mono=True,
                          anchor="middle"),
                     arrow([(x0 + 60, 92), (x0 + 60, 119),
                            (x0 + 112, 119)], kind="trace"),
                     text(x0 + 66, 113, "parent", size=11.5,
                          italic=True)]
        body += [text(x0 + 110, 196, note1, size=11.5, anchor="middle"),
                 text(x0 + 110, 211, note2, size=11.5, anchor="middle")]
    return svg(220, body)


def linked_receipts():
    """Figure 5.4. Two receipts, two companies, one chain of custody."""
    rows_a = [("who", "Speedy, first party"),
              ("tool", "disputes.open"),
              ("via", "a2a"), ("trace", "3f1a8c27…"),
              ("id", "rcpt_3f1a8c27…a450")]
    rows_b = [("who", "Ledger, third party"),
              ("tool", "orders.get"),
              ("via", "mcp"), ("trace", "c4e81b0f…"),
              ("parent", "rcpt_3f1a8c27…a450")]
    body = []
    for x, title, rows in [(4, "Receipt 04", rows_a),
                           (246, "Receipt 05", rows_b)]:
        body += [receipt(x, 6, 210, 136, width=1.6),
                 text(x + 10, 24, title, size=12, weight=700)]
        for i, (key, value) in enumerate(rows):
            y = 46 + i * 18
            body += [text(x + 10, y, key, size=11.5, mono=True),
                     text(x + 200, y, value, size=11.5, anchor="end",
                          fill=MID)]
    body += [arrow([(244, 118), (218, 118)], kind="trace"),
             text(231, 160, "parent_receipt_id", size=11.5, mono=True,
                  anchor="middle"),
             line([(231, 122), (231, 148)], width=0.8),
             text(4, 186, "The join: Ledger returned its trace ID "
                  "(c4e81b0f…) to Speedy.", size=11.5),
             text(4, 202, "Pronto's MCP server span for Ledger's read is "
                  "in that trace,", size=11.5),
             text(4, 218, "so Pronto can link the two receipts without "
                  "seeing PayCo's spans.", size=11.5)]
    return svg(228, body)


FIGURES = {"fig-5-1-receipt-strip": lambda: receipt_strip({4}),
           "fig-5-2-conversation-swimlane": swimlane,
           "fig-5-3-continue-or-link": continue_or_link,
           "fig-5-4-linked-receipts": linked_receipts}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
