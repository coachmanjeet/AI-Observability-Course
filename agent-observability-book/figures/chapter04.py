"""Chapter 4 figures: the annotated trace, span to receipt, and the
three ways instrumentation reaches one schema.

Usage: python -m figures.chapter04 OUT_DIR

Figure 4.2 is drawn from traces/speedy-refund-40.json, so the numbers
in the figure always match the trace the lab produces.
"""
import pathlib
import sys
import textwrap

from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, WIDTH, arrow, badge, box,
                              gate, line, receipt, store, svg, text)
from telemetry import otlp
from telemetry.waterfall import depth

HERE = pathlib.Path(__file__).parent.parent
TRACE = HERE / "traces" / "speedy-refund-40.json"

CALLOUTS = [  # (row, note)
    (0, "One invoke_agent span per agent turn. It names the agent, "
        "its version and the conversation."),
    (1, "Each model call is a CLIENT span with the provider, the model "
        "and the tokens it used."),
    (2, "Each tool call is its own span, carrying the tool-call ID the "
        "model chose."),
    (4, "One model response asked for two tools; both spans hang off "
        "the same agent span."),
    (6, "The refund decision: 19 of the turn's 39 seconds and 410 "
        "output tokens."),
    (7, "The span a receipt is built from: what it touched, a digest "
        "of its arguments, and what changed."),
]


def annotated_trace(path=TRACE):
    """Figure 4.2. Speedy's $40 refund as a waterfall, with callouts."""
    spans = otlp.load(path)
    by_id = {s["span_id"]: s for s in spans}
    t0 = min(s["start"] for s in spans)
    total = (max(s["end"] for s in spans) - t0) / 1e9
    x0, x1, top, pitch = 206, 404, 34, 24
    scale = (x1 - x0) / 40
    body = []
    for sec in range(0, 41, 10):
        x = x0 + sec * scale
        body += [line([(x, top - 8), (x, top + 9 * pitch)], width=0.6,
                      dash="2 3", color=MID),
                 text(x, top - 12, f"{sec} s", size=11.5, anchor="middle",
                      fill=MID)]
    marks = {row: n for n, (row, _) in enumerate(CALLOUTS, 1)}
    for i, s in enumerate(spans):
        y = top + i * pitch
        op = s["attributes"]["gen_ai.operation.name"]
        start = (s["start"] - t0) / 1e9
        dur = (s["end"] - s["start"]) / 1e9
        fill = {"invoke_agent": PALE, "chat": FILL}.get(op, "#ffffff")
        body += [text(26 + depth(s, by_id) * 10, y + 15, s["name"],
                      size=11.5, weight=600 if op == "invoke_agent"
                      else 400),
                 box(x0 + start * scale, y + 5, max(2.5, dur * scale), 13,
                     fill=fill, width=1.0),
                 text(WIDTH - 2, y + 15, f"{dur:.2f} s", size=11.5,
                      anchor="end")]
        if i in marks:
            body.append(badge(11, y + 11, str(marks[i]), size=11.5))
    y = top + 9 * pitch + 14
    body.append(text(4, y + 4, f"Total {total:.1f} s. Gray bars are "
                     "model calls; white bars are tool calls.",
                     size=11.5, italic=True))
    y += 18
    for n, (_, note) in enumerate(CALLOUTS, 1):
        wrapped = textwrap.wrap(note, 66)
        body += [badge(11, y + 10, str(n), size=11.5),
                 text(26, y + 14, "\n".join(wrapped), size=11.5)]
        y += 14 * len(wrapped) + 9
    return svg(y + 4, body)


SPAN_GROUPS = [  # (receipt section it feeds, [(key, value, level)])
    ("evidence", [("trace_id", "4bf92f35…0e4736", "span identity"),
                  ("span_id", "00f067aa0ba902b7", "span identity"),
                  ("gen_ai.conversation.id", "conv_44be2d",
                   "cond. required")]),
    ("who", [("parent span", "invoke_agent Speedy", "span identity")]),
    ("issued_at", [("end time", "02:07:13.28 UTC", "span timing")]),
    ("did_what.action", [
        ("gen_ai.operation.name", "execute_tool", "required"),
        ("gen_ai.tool.name", "refunds.create", "required"),
        ("gen_ai.tool.call.id", "call_8c21", "recommended"),
        ("pronto.tool.target", "order:ord_5521", "Pronto's own"),
        ("pronto.tool.arguments_digest", "sha256:6c5c…",
         "Pronto's own")]),
    ("did_what.effect", [
        ("pronto.effect.status", "succeeded", "Pronto's own"),
        ("pronto.effect.ref", "refund:rf_9931", "Pronto's own"),
        ("pronto.effect.amount", "40.00", "Pronto's own")]),
    (None, [("gen_ai.tool.call.arguments", "not captured", "opt-in, off"),
            ("gen_ai.tool.call.result", "not captured", "opt-in, off")]),
]


def span_to_receipt():
    """Figure 4.4. One execute_tool span, grouped by the receipt
    section each attribute feeds."""
    pitch = 18
    body = [text(8, 19, "execute_tool refunds.create", size=12,
                 weight=700, mono=True),
            text(WIDTH - 6, 19, "requirement", size=11.5, anchor="end",
                 italic=True, fill=MID)]
    y = 30
    for field, rows in SPAN_GROUPS:
        y += 8
        if field:
            body += [receipt(8, y, 16, 14, fill=PALE, width=1.0),
                     text(30, y + 11, "feeds", size=11.5, italic=True),
                     text(64, y + 11, field, size=11.5, weight=700,
                          mono=True)]
        else:
            body.append(text(8, y + 11, "feeds nothing: content stays "
                             "out of receipts", size=11.5, italic=True))
        y += 17
        for key, value, level in rows:
            off = field is None
            body += [text(30, y + 11, key, size=11.5, mono=True,
                          fill=MID if off else "#000000"),
                     text(336, y + 11, value, size=11.5, anchor="end",
                          italic=off, fill=MID),
                     text(WIDTH - 6, y + 11, level, size=11.5,
                          anchor="end", fill=MID)]
            y += pitch
    body.insert(0, box(0, 4, WIDTH, 22, fill=PALE))
    body.insert(0, box(0, 4, WIDTH, y + 4))
    return svg(y + 10, body)


def instrumentation_paths():
    """Figure 4.3. Three ways in, one schema, many consumers."""
    sources = [
        ("Hand-instrumented", "Speedy, this chapter", "1P"),
        ("Framework-native", "Agent Framework, ADK,\nStrands", "1P"),
        ("Instrumentor libraries", "OTel contrib, OpenLLMetry,\n"
         "OpenInference", "3P"),
    ]
    body = []
    for i, (title, note, kind) in enumerate(sources):
        y = 10 + i * 78
        body += [box(0, y, 160, 62),
                 text(80, y + 21, title, size=11.5, weight=700,
                      anchor="middle"),
                 text(80, y + 37, note, size=11.5, anchor="middle"),
                 arrow([(162, y + 31), (186, 41 + 78)], kind="trace")]
    body += [box(188, 86, 104, 66, fill=FILL, width=2.0),
             text(240, 106, "Collector", size=12, weight=700,
                  anchor="middle"),
             text(240, 122, "normalizes to", size=11.5, anchor="middle"),
             text(240, 137, "gen_ai.* (Ch 6)", size=11.5, anchor="middle")]
    outs = [("store", "Any OTLP backend"), ("gate", "telemetry.lint"),
            ("receipt", "receipts.from_trace")]
    for i, (shape, label) in enumerate(outs):
        y = 18 + i * 78
        body.append(arrow([(294, 119), (318, y + 22)], kind="trace"))
        if shape == "store":
            body.append(store(320, y, 140, 44, label, size=11.5))
        elif shape == "gate":
            body += [gate(338, y + 22, 18), text(362, y + 26, label,
                                                  size=11.5, mono=True)]
        else:
            body += [receipt(320, y, 140, 44),
                     text(390, y + 26, label, size=11.5, mono=True,
                          anchor="middle")]
    body.append(text(230, 252, "Instrument once on the conventions. "
                     "Normalize the rest in the Collector.", size=11.5,
                     italic=True, anchor="middle"))
    return svg(262, body)


FIGURES = {"fig-4-1-receipt-strip": lambda: receipt_strip({0, 4}),
           "fig-4-2-annotated-trace": annotated_trace,
           "fig-4-3-instrumentation-paths": instrumentation_paths,
           "fig-4-4-span-to-receipt": span_to_receipt}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
