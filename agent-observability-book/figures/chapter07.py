"""Chapter 6 figures, drawn from the lab's own measurements: the
pipeline with what each stage kept, and the incidents each kind of
sampling kept.

Usage: python -m figures.chapter07 OUT_DIR
"""
import json
import pathlib
import sys
import tempfile

from collector import processors as p
from collector.night import canaries, night
from figures.chapter02 import receipt_strip
from figures.notation import (FILL, MID, PALE, agent, arrow, box, line,
                              receipt, store, svg, text)
from telemetry import otlp


def measure():
    """The night's numbers, measured the way collector.run does."""
    spans, plan = night()
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp)
        otlp.write(spans, path / "r.json")
        received = otlp.load(path / "r.json")
        redacted = p.redact(received)
        kept, _ = p.tail_sample(redacted)
        stages = []
        for name, s in [("received", received), ("redacted", redacted),
                        ("kept", kept)]:
            size = otlp.write_plain(s, path / f"{name}.json")
            stages.append({"name": name, "traces": len(p.traces(s)),
                           "spans": len(s), "mb": size / 1e6,
                           "pii": p.leaks(s, canaries(plan))})
    trouble = p.incidents(redacted)
    head = set(p.traces(p.head_sample(redacted)))
    return {"stages": stages, "incidents": len(trouble),
            "head": len(trouble & head),
            "tail": len(trouble & set(p.traces(kept)))}


def pipeline(m):
    """Figure 7.2. Redact first, fork, then sample."""
    received, redacted, kept = m["stages"]
    body = [
        agent(4, 30, 86, 50, "Speedy\nruntime", size=11.5),
        arrow([(90, 55), (112, 55)], kind="call"),
        box(114, 22, 214, 66, fill="none", width=1.0, kind="boundary"),
        text(120, 16, "Collector", size=11.5, italic=True),
        box(124, 34, 86, 42, fill=PALE),
        text(167, 52, "redact", size=12, weight=600, anchor="middle"),
        text(167, 68, "allowlist", size=11.5, anchor="middle"),
        arrow([(210, 55), (230, 55)], kind="call"),
        box(232, 34, 88, 42, fill=PALE),
        text(276, 52, "tail-sample", size=12, weight=600,
             anchor="middle"),
        text(276, 68, "keep incidents", size=11.5, anchor="middle"),
        arrow([(320, 55), (352, 55)], kind="call"),
        store(354, 28, 102, 56, "trace\nbackend", size=11.5),
        line([(220, 55), (220, 112)], width=1.6),
        arrow([(220, 112), (352, 112)], kind="call"),
        receipt(354, 96, 102, 40),
        text(405, 120, "receipt builder", size=11.5, anchor="middle"),
        text(228, 106, "every redacted span", size=11.5, italic=True),
    ]
    top = 166
    body += [text(4, top, "What each stage holds (one night, 1,000 "
                  "conversations)", size=11.5, weight=600)]
    widest = received["mb"]
    for i, (s, label) in enumerate([(received, "received"),
                                    (redacted, "after redaction"),
                                    (kept, "after tail sampling")]):
        y = top + 16 + i * 48
        w = 300 * s["mb"] / widest
        body += [box(4, y, w, 22, fill=FILL if i < 2 else PALE),
                 text(w + 10, y + 16, f"{s['mb']:.1f} MB", size=11.5,
                      weight=600),
                 text(4, y + 38, f"{label}: {s['traces']:,} traces, "
                      f"{s['spans']:,} spans, {s['pii']:,} PII values",
                      size=11.5, fill=MID)]
    return svg(top + 16 + 3 * 48 + 2, body)


def incidents(m):
    """Figure 7.3. The same night, sampled two ways."""
    n = m["incidents"]
    body = []
    for row, (label, got) in enumerate([("Head sampling at 10%",
                                         m["head"]),
                                        ("Tail sampling", m["tail"])]):
        y = 18 + row * 92
        body.append(text(4, y, f"{label}: kept {got} of {n} incidents",
                         size=12, weight=600))
        for i in range(n):
            cx, cy = 10 + (i % 23) * 19.6, y + 20 + (i // 23) * 22
            fill = "#000000" if i < got else "#ffffff"
            body.append(f'<circle cx="{cx}" cy="{cy}" r="6.5" '
                        f'fill="{fill}" stroke="#000000" '
                        'stroke-width="1.2"/>')
    body.append(text(4, 196, "Filled: the trace was kept. Incidents: errors, and "
                     "turns slower than 30 s.", size=11.5, fill=MID))
    return svg(204, body)


def build(out):
    m = measure()
    figures = {"fig-7-1-receipt-strip": receipt_strip({5}),
               "fig-7-2-pipeline": pipeline(m),
               "fig-7-3-incidents-kept": incidents(m)}
    for name, drawing in figures.items():
        (out / f"{name}.svg").write_text(drawing, encoding="utf-8")
        print("wrote", out / f"{name}.svg")
    return m


FIGURES = {"fig-7-1-receipt-strip": lambda: receipt_strip({5}),
           "fig-7-2-pipeline": lambda: pipeline(measure()),
           "fig-7-3-incidents-kept": lambda: incidents(measure())}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    print(json.dumps(build(out)["stages"]))
