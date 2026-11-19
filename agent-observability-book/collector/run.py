"""Saturday night through the Collector (Chapter 7).

Usage: python -m collector.run OUT_DIR [--allow KEY ...]

Generates the night's traffic, then runs it through the pipeline in
the order a production Collector should: redact first, build receipts
from the redacted spans, then tail-sample what goes to the trace
backend. Prints what each stage kept, and what it cost.
"""
import argparse
import contextlib
import io
import json
import pathlib
from decimal import Decimal

from collector import processors as p
from collector.night import canaries, night
from collector.prices import TRACES_PER_1K, TRACES_PER_GB, model_cost
from receipts.from_trace import load_inventory, receipts
from receipts.validate import check, unanswered
from telemetry import otlp

FLEET = pathlib.Path(__file__).parent.parent / "maturity" / "fleet.json"


def row(name, spans, size, found):
    return (f"{name:<14}{len(p.traces(spans)):>7,}{len(spans):>8,}"
            f"{size / 1e6:>7.1f} MB{found:>11,}")


def night_cost(spans):
    total = Decimal(0)
    for s in spans:
        a = s["attributes"]
        if a.get("gen_ai.operation.name") == "chat":
            total += Decimal(model_cost(
                a["gen_ai.request.model"], a["gen_ai.usage.input_tokens"],
                a["gen_ai.usage.output_tokens"],
                a.get("gen_ai.usage.cache_read.input_tokens", 0)))
    return total


def write_receipts(spans, out):
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for n, rec in enumerate(receipts(spans, load_inventory(FLEET),
                                     with_cost=True), 1):
        path = out / f"{n:04d}.json"
        path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    with contextlib.redirect_stdout(io.StringIO()):
        ok = check(paths)
    answers = {7 - len(unanswered(json.loads(x.read_text())))
               for x in paths}
    return len(paths), ok, answers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--allow", action="append", default=[],
                        help="add a key to the allowlist (the lab's "
                        "mistake on purpose)")
    args = parser.parse_args(argv)
    raw_spans, plan = night()
    otlp.write(raw_spans, args.out / "night-received.json")
    received = otlp.load(args.out / "night-received.json")
    found = canaries(plan)
    redacted = p.redact(received, p.ALLOWED_KEYS | set(args.allow))
    kept, reasons = p.tail_sample(redacted)
    sizes = [otlp.write_plain(received, args.out / "night-received.json"),
             otlp.write_plain(redacted, args.out / "night-redacted.json"),
             otlp.write_plain(kept, args.out / "night-sampled.json")]
    print(f"{'Stage':<14}{'traces':>7}{'spans':>8}{'size':>10}"
          f"{'PII values':>11}")
    for name, spans, size in [("received", received, sizes[0]),
                              ("redacted", redacted, sizes[1]),
                              ("tail-sampled", kept, sizes[2])]:
        print(row(name, spans, size, p.leaks(spans, found)))
    dropped, masked = (sum(s["attributes"].get(f"redaction.{k}.count", 0)
                           for s in redacted)
                       for k in ("redacted", "masked"))
    print(f"\nRedaction dropped {dropped:,} attributes and masked "
          f"{masked} values")
    trouble = p.incidents(redacted)
    head = set(p.traces(p.head_sample(redacted)))
    tail = set(p.traces(kept))
    print(f"Incidents (errors and slow turns): {len(trouble)}")
    print(f"  head sampling at 10% kept {len(trouble & head):>4}")
    print(f"  tail sampling kept        {len(trouble & tail):>4}")
    why = ", ".join(f"{n} {k}" for k, n in reasons.most_common())
    print(f"Tail sampling kept {len(tail)} traces:\n  {why}")
    count, ok, answers = write_receipts(redacted,
                                        args.out / "receipts")
    span = " to ".join(str(n) for n in sorted(answers))
    print(f"\nReceipts, built before sampling: {count:,}\n  "
          f"{'PASS' if ok else 'FAIL'}, each R1 with {span} of 7 answers")
    per_gb = [Decimal(n) / Decimal(10 ** 9) * TRACES_PER_GB
              for n in (sizes[0], sizes[2])]
    per_trace = [Decimal(len(p.traces(s))) / 1000 * TRACES_PER_1K
                 for s in (received, kept)]
    print(f"\nModel calls for the night: ${night_cost(received):.2f}")
    print(f"Traces at ${TRACES_PER_GB}/GB:      ${per_gb[0]:.4f} "
          f"received, ${per_gb[1]:.4f} kept")
    print(f"Traces at ${TRACES_PER_1K} per 1,000: ${per_trace[0]:.2f} "
          f"received, ${per_trace[1]:.2f} kept")


if __name__ == "__main__":
    main()
