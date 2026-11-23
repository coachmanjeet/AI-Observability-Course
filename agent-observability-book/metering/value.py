"""From telemetry to business value (Chapter 21).

Usage: python -m metering.value [OUT_DIR]

Runs a month of Speedy's conversations for Pronto, then joins
three layers the way a value dashboard must: technical (model
cost from the chat spans), behavioral (what each conversation
did, from the tool spans) and business (whether the customer's
problem stayed solved for seven days, from follow-ups). The
result is a driver tree with one outcome metric, a cost per
outcome, and an outcome record for every first contact.

Cost comes from usage records, one per model call, written before
any trace sampling and deduplicated by span ID, so cutting trace
retention changes what engineers can inspect and nothing finance
reports. The last block of the output proves it.
"""
import hashlib
import json
import pathlib
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal

from collector.prices import model_cost
from metering.traffic import day, month

METRIC = "resolved_without_escalation_within_7d"
# The customer outcome both arms are judged on: the issue stayed
# solved for its window, whoever handled it (Chapter 21's memo).
CUSTOMER = "issue_resolved_within_window"
REDELIVERED = 0.02    # exporter retries: same record sent twice
RETAIN = 0.30         # the trace retention finance asked about
HUMAN_PER_CONTACT = Decimal("5.80")   # Pronto finance, Jan 2027
START = day("2027-02-01")


def unit(key):
    """A stable number in [0, 1) from a key: same key, same answer."""
    h = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


def usage_records(spans, redelivered=REDELIVERED):
    """One small record per model call, written as the span ends,
    before sampling. A share are delivered twice, as at-least-once
    exporters do; the span ID is the record's key."""
    out = []
    for s in spans:
        a = s.attributes
        if a.get("gen_ai.operation.name") != "chat":
            continue
        rec = {"key": f"{s.context.span_id:016x}",
               "trace_id": f"{s.context.trace_id:032x}",
               "conversation_id": a["gen_ai.conversation.id"],
               "model": a["gen_ai.request.model"],
               "cost": Decimal(model_cost(
                   a["gen_ai.request.model"],
                   a["gen_ai.usage.input_tokens"],
                   a["gen_ai.usage.output_tokens"],
                   a.get("gen_ai.usage.cache_read.input_tokens",
                         0)))}
        out.append(rec)
        if unit("dup:" + rec["key"]) < redelivered:
            out.append(dict(rec))
    return out


def dedupe(records):
    """Keep the first record for each key. A retried model call is
    a new span with its own key, and its cost is real: it stays."""
    seen, out = set(), []
    for r in records:
        if r["key"] not in seen:
            seen.add(r["key"])
            out.append(r)
    return out


def by_conversation(spans, usage=None):
    """Cost from usage records; tools and refunds from spans."""
    out = defaultdict(lambda: {"cost": Decimal(0), "tools": [],
                               "refund": Decimal(0)})
    for r in dedupe(usage_records(spans) if usage is None
                    else usage):
        out[r["conversation_id"]]["cost"] += r["cost"]
    for s in spans:
        a = s.attributes
        conv = a.get("gen_ai.conversation.id")
        if not conv:
            continue
        tool = a.get("gen_ai.tool.name")
        if tool:
            out[conv]["tools"].append(tool)
            if tool == "refunds.create":
                out[conv]["refund"] += Decimal(
                    a.get("pronto.effect.amount", "0"))
    return out


def outcomes(convs, per):
    """One outcome per first contact, known seven days later."""
    back = defaultdict(list)
    for c in convs:
        if c["follow_up"]:
            back[c["order_id"]].append(c["at"])
    rows = []
    for c in convs:
        if c["follow_up"]:
            continue
        tools = per[c["conversation_id"]]["tools"]
        due = c["at"] + timedelta(days=7)
        returned = any(c["at"] < t <= due
                       for t in back[c["order_id"]])
        if "cases.escalate" in tools:
            why = "escalated"
        elif returned:
            why = "came back"
        else:
            why = "resolved"
        rows.append({"conversation_id": c["conversation_id"],
                     "timeout": c["timeout"], "why": why,
                     "status": ("achieved" if why == "resolved"
                                else "not_achieved"),
                     "due": due})
    return rows


def record(row):
    ok = row["status"] == "achieved"
    return {"record_type": "outcome", "status": row["status"],
            "metric": METRIC,
            "recorded_at":
                row["due"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evidence": {"evaluation": {
                "name": "resolved_without_escalation",
                "score_value": 1 if ok else 0,
                "score_label": "pass" if ok else "fail"}}}


def tree(convs, per, rows):
    first = len(rows)
    why = Counter(r["why"] for r in rows)
    back_after = Counter("timeout" if r["timeout"] else "other"
                         for r in rows
                         if r["why"] == "came back")
    cost = sum((v["cost"] for v in per.values()), Decimal(0))
    paid = sum((v["refund"] for v in per.values()), Decimal(0))
    refunds = sum(v["tools"].count("refunds.create")
                  for v in per.values())
    res = why["resolved"]
    people = HUMAN_PER_CONTACT * why["escalated"]
    return {"conversations": len(convs), "first": first,
            "resolved": res, "came_back": why["came back"],
            "customer": first - why["came back"],
            "back_after_timeout": back_after["timeout"],
            "escalated": why["escalated"], "cost": cost,
            "per_conv": cost / len(convs),
            "per_resolved": cost / res, "people": people,
            "model_people": (cost + people) / res,
            "paid": paid, "refunds": refunds,
            "human": HUMAN_PER_CONTACT * len(convs)}


def retention(spans, convs, rows, keep=RETAIN):
    """Cut trace retention to `keep` and compare what each source
    still says. Stored traces are a diagnostic sample; usage records
    are the population."""
    usage = dedupe(usage_records(spans))
    kept = {r["trace_id"] for r in usage
            if unit("keep:" + r["trace_id"]) < keep}
    stored = [s for s in spans
              if f"{s.context.trace_id:032x}" in kept]
    stored_convs = {s.attributes.get("gen_ai.conversation.id")
                    for s in stored} - {None}
    from_traces = sum((r["cost"] for r in usage
                       if r["trace_id"] in kept), Decimal(0))
    t = tree(convs, by_conversation(spans, usage), rows)
    return {"stored": len(stored_convs), "all": len(convs),
            "traces_cost": from_traces, "usage_cost": t["cost"],
            "model_people": t["model_people"],
            "records": len(usage_records(spans)),
            "kept_records": len(usage)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    spans, convs = month("tenant:pronto", START, 28)
    per = by_conversation(spans)
    rows = outcomes(convs, per)
    t = tree(convs, per, rows)
    r = retention(spans, convs, rows)
    pct = 100 * t["resolved"] / t["first"]
    print("Speedy for Pronto, Feb 2027: driver tree")
    print(f"conversations            {t['conversations']:>7,}")
    print(f"  first contacts         {t['first']:>7,}")
    print(f"    resolved in 7 days   {t['resolved']:>7,}  "
          f"{pct:.1f}%")
    print(f"    came back            {t['came_back']:>7,}  "
          f"({t['back_after_timeout']} after a timeout)")
    print(f"    escalated            {t['escalated']:>7,}")
    cpct = 100 * t["customer"] / t["first"]
    print(f"  customer outcome       {t['customer']:>7,}  "
          f"{cpct:.1f}%, any handler")
    print(f"model cost               ${t['cost']:.2f}")
    print(f"  per conversation       ${t['per_conv']:.4f}")
    print(f"  per resolved           ${t['per_resolved']:.4f}")
    print(f"escalations to people    ${t['people']:,.2f}")
    print(f"model + escalation       ${t['model_people']:.3f} "
          "per resolved")
    print(f"refunds paid             ${t['paid']:,.2f} on "
          f"{t['refunds']} refunds")
    print(f"scenario: all by people  ${t['human']:,.2f}")
    dup = r["records"] - r["kept_records"]
    print(f"Trace retention cut to {RETAIN:.0%}")
    print(f"  usage records          {r['kept_records']:>7,}; "
          f"{dup} resent, dropped")
    print(f"  conversations traced   {r['stored']:>7,} of "
          f"{r['all']:,}")
    print(f"  model cost, traces     ${r['traces_cost']:.2f}")
    print(f"  model cost, usage      ${r['usage_cost']:.2f}  "
          "unchanged")
    print(f"  model + escalation     ${r['model_people']:.3f} "
          "unchanged")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        good = next(r for r in rows
                    if r["status"] == "achieved")
        rec = record(good)
        (out / "outcome-record.json").write_text(
            json.dumps(rec, indent=2) + "\n")
        (out / "receipt-outcome.json").write_text(json.dumps(
            {"did_what": {"outcome": {
                "status": "pending", "metric": METRIC}}},
            indent=2) + "\n")


if __name__ == "__main__":
    main()
