"""Replays Saturday night as Pronto could see it on Monday morning.

Usage: python -m incident.replay

Used in Chapter 1. Reads the payments API's log for the night, finds
the evidence behind each refund (Speedy's trace from Chapter 4, and
Night Owl's thin receipt from Chapter 2), and shows which of the
receipt's seven questions each refund can answer.
"""
import json
import pathlib

from receipts.from_trace import load_inventory, receipts
from receipts.validate import QUESTIONS, unanswered
from telemetry import otlp

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
LOG = HERE / "payments-2026-11-14.jsonl"
TRACE = ROOT / "traces" / "speedy-refund-40.json"
EXAMPLES = ROOT / "receipts" / "examples"


def payments():
    """The payments API's own log lines for the night."""
    lines = LOG.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def evidence():
    """Map each refund ID to (what it left behind, its receipt)."""
    spans = otlp.load(TRACE)
    inventory = load_inventory(ROOT / "maturity" / "fleet.json")
    found = {}
    for rec in receipts(spans, inventory):
        ref = rec["did_what"]["effect"].get("external_ref", "")
        if ref.startswith("refund:"):
            trace = rec["evidence"]["trace_id"]
            n = sum(s["trace_id"] == trace for s in spans)
            what = (f"trace {trace[:8]}: {n} spans, refund span "
                    f"{rec['evidence']['span_id'][:8]}")
            found[ref[len("refund:"):]] = (what, rec)
    owl = EXAMPLES / "04-night-owl-refund-85-R1.json"
    rec = json.loads(owl.read_text(encoding="utf-8"))
    ref = rec["did_what"]["effect"]["external_ref"]
    found[ref[len("refund:"):]] = ("the payments log line, "
                                   "nothing else", rec)
    return found


def age(line):
    """Days between the credential's issue date and the call."""
    from datetime import date
    issued = date.fromisoformat(line["credential_issued"])
    used = date.fromisoformat(line["time"][:10])
    return (used - issued).days


def main():
    night = payments()
    found = evidence()
    print("Saturday, Nov 14, 2026, as the payments API logged it")
    for p in night:
        print(f"{p['time'][11:19]}  {p['refund']}  ${p['amount']}  "
              f"{p['order']}  {p['caller']}")
        days = age(p)
        print(f"          {p['credential']}, issued {days} day"
              f"{'' if days == 1 else 's'} earlier")
    print()
    print("What each refund left behind")
    for p in night:
        print(f"{p['refund']}  {found[p['refund']][0]}")
    print()
    ids = [p["refund"] for p in night]
    head = "".join(f"{r:<10}" for r in ids)
    print(f"{'question':<18}{head}".rstrip())
    gaps = {r: unanswered(found[r][1]) for r in ids}
    for _, label in QUESTIONS:
        row = "".join(f"{'no' if label in gaps[r] else 'yes':<10}"
                      for r in ids)
        print(f"{label:<18}{row}".rstrip())
    row = "".join(f"{7 - len(gaps[r])} of 7    " for r in ids)
    print(f"{'answered':<18}{row.rstrip()}")
    print()
    target = EXAMPLES / "02-speedy-refund-40.json"
    full = json.loads(target.read_text(encoding="utf-8"))
    print(f"By Chapter 34: rf_9931's receipt answers "
          f"{7 - len(unanswered(full))} of 7 "
          f"({full['conformance']}, chained)")


if __name__ == "__main__":
    main()
