"""From telemetry to business value (Chapter 21).

Usage: python -m metering.value [OUT_DIR]

Runs a month of Speedy's conversations for Pronto, then joins
three layers the way a value dashboard must: technical (model
cost from the chat spans), behavioral (what each conversation
did, from the tool spans) and business (whether the customer's
problem stayed solved for seven days, from follow-ups). The
result is a driver tree with one outcome metric, a cost per
outcome, and an outcome record for every first contact.

Escalations count as customer resolutions only on evidence: the
support case behind each one must have closed and stayed closed
for seven days. The help desk is simulated here, seeded by
conversation, so some cases are still open, some reopened, and
some escalations have no case record at all. Nothing assumes an
escalation succeeded.

Cost comes from usage records, one per model call, written before
any trace sampling. A record is identified by tenant, trace ID and
span ID together, so a resent record counts once and two traces
that happen to share a span ID both count. The last block of the
output shows that cutting trace retention changes what engineers
can inspect and nothing finance reports.
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
AS_OF = day("2027-04-19") + timedelta(hours=9)   # the review
# The simulated help desk: no case record, still open, reopened
NO_CASE, STILL_OPEN, REOPENED = 0.03, 0.02, 0.05
TENANT = "tenant:pronto"


def unit(key):
    """A stable number in [0, 1) from a key: same key, same answer."""
    h = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


def usage_records(spans, redelivered=REDELIVERED, tenant=TENANT):
    """One small record per model call, written as the span ends,
    before sampling. A share are delivered twice, as at-least-once
    exporters do."""
    out = []
    for s in spans:
        a = s.attributes
        if a.get("gen_ai.operation.name") != "chat":
            continue
        rec = {"tenant": tenant,
               "trace_id": f"{s.context.trace_id:032x}",
               "span_id": f"{s.context.span_id:016x}",
               "conversation_id": a["gen_ai.conversation.id"],
               "model": a["gen_ai.request.model"],
               "cost": Decimal(model_cost(
                   a["gen_ai.request.model"],
                   a["gen_ai.usage.input_tokens"],
                   a["gen_ai.usage.output_tokens"],
                   a.get("gen_ai.usage.cache_read.input_tokens",
                         0)))}
        out.append(rec)
        if unit("dup:" + rec["span_id"]) < redelivered:
            out.append(dict(rec))
    return out


def usage_key(r):
    """A span ID is unique only within its trace, and a trace ID
    only within its tenant's telemetry: the key needs all three."""
    return (r["tenant"], r["trace_id"], r["span_id"])


def dedupe(records):
    """Keep the first record for each key. A retried model call is
    a new span with its own key, and its cost is real: it stays."""
    seen, out = set(), []
    for r in records:
        if usage_key(r) not in seen:
            seen.add(usage_key(r))
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


def case(c):
    """The help desk's record of the case behind an escalation,
    or None when there is no case for it. Simulated, seeded by
    conversation, as of the review."""
    cid = c["conversation_id"]
    if unit("case:" + cid) < NO_CASE:
        return None
    rec = {"case_id": "case_" + cid[5:11], "closed_at": None,
           "reopened_at": None}
    if unit("open:" + cid) < STILL_OPEN:
        return rec                       # waiting on a supplier
    rec["closed_at"] = c["at"] + timedelta(
        hours=4 + 44 * unit("close:" + cid))
    if unit("reopen:" + cid) < REOPENED:
        rec["reopened_at"] = rec["closed_at"] + timedelta(
            days=1 + 5 * unit("again:" + cid))
    return rec


def customer(why, case, as_of=AS_OF):
    """Did the issue stay resolved? Only on evidence."""
    if why == "resolved":
        return "resolved"
    if why == "came back":
        return "not resolved"
    if case is None:
        return "unknown"         # no case record: can't confirm
    closed, again = case["closed_at"], case["reopened_at"]
    if closed is None:
        return "pending"         # still open
    if again and again <= closed + timedelta(days=7):
        return "not resolved"    # reopened within 7 days
    if closed + timedelta(days=7) > as_of:
        return "pending"         # its 7 days aren't over yet
    return "resolved"


def outcomes(convs, per, as_of=AS_OF):
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
        cs = case(c) if why == "escalated" else None
        rows.append({"conversation_id": c["conversation_id"],
                     "timeout": c["timeout"], "why": why,
                     "status": ("achieved" if why == "resolved"
                                else "not_achieved"),
                     "case": cs,
                     "customer": customer(why, cs, as_of),
                     "due": due})
    return rows


def record(row):
    ok = row["status"] == "achieved"
    return {"record_type": "outcome", "status": row["status"],
            "metric": METRIC,
            "recorded_at":
                row["due"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evidence": {
                "source": "pronto://conversations?order_window=7d",
                "evaluation": {
                "name": "resolved_without_escalation",
                "score_value": 1 if ok else 0,
                "score_label": "pass" if ok else "fail"}}}


def case_record(row):
    """The customer outcome for an escalation, with the help desk's
    case as its evidence. Pending cases get no record yet."""
    status = {"resolved": "achieved", "not resolved": "not_achieved",
              "unknown": "unknown"}[row["customer"]]
    cs = row["case"]
    label = {"achieved": "closed, not reopened in 7 days",
             "not_achieved": "reopened within 7 days",
             "unknown": "no case record found"}[status]
    when = (cs["closed_at"] + timedelta(days=7)) if cs else AS_OF
    return {"record_type": "outcome", "status": status,
            "metric": CUSTOMER,
            "recorded_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evidence": {
                "source": (f"helpdesk://pronto/cases/{cs['case_id']}"
                           if cs else "helpdesk://pronto/cases?"
                           f"conversation={row['conversation_id']}"),
                "evaluation": {"name": "case_stayed_closed",
                               "score_value": 1 if status ==
                               "achieved" else 0,
                               "score_label": label}}}


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
    cust = Counter(r["customer"] for r in rows)
    esc = Counter(r["customer"] for r in rows
                  if r["why"] == "escalated")
    confirmed = cust["resolved"]
    return {"conversations": len(convs), "first": first,
            "resolved": res, "came_back": why["came back"],
            "customer": confirmed, "esc": esc,
            "pending": cust["pending"], "unknown": cust["unknown"],
            "mature": first - cust["pending"],
            "per_confirmed": cost / confirmed,
            "confirmed_cost": (cost + people) / confirmed,
            "back_after_timeout": back_after["timeout"],
            "escalated": why["escalated"], "cost": cost,
            "per_conv": cost / len(convs),
            "per_resolved": cost / res, "people": people,
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
            "confirmed_cost": t["confirmed_cost"],
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
    e = t["esc"]
    print("Speedy for Pronto, Feb 2027: driver tree")
    print(f"conversations            {t['conversations']:>7,}")
    print(f"  first contacts         {t['first']:>7,}")
    print(f"    resolved by Speedy   {t['resolved']:>7,}  "
          f"{pct:.1f}%, autonomy")
    print(f"    came back            {t['came_back']:>7,}  "
          f"({t['back_after_timeout']} after a timeout)")
    print(f"    escalated            {t['escalated']:>7,}")
    print(f"      case stayed closed {e['resolved']:>7,}")
    print(f"      case reopened      {e['not resolved']:>7,}")
    print(f"      case still open    {e['pending']:>7,}  pending")
    print(f"      no case record     {e['unknown']:>7,}  unknown")
    cpct = 100 * t["customer"] / t["mature"]
    print(f"customer resolutions     {t['customer']:>7,} of "
          f"{t['mature']:,} mature  {cpct:.1f}%")
    print(f"model cost               ${t['cost']:.2f}")
    print(f"  per conversation       ${t['per_conv']:.4f}")
    print(f"  per confirmed          ${t['per_confirmed']:.4f}")
    print(f"escalations to people    ${t['people']:,.2f}")
    print(f"model + escalation       ${t['confirmed_cost']:.3f} "
          "per confirmed")
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
    print(f"  model + escalation     ${r['confirmed_cost']:.3f} "
          "unchanged")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        good = next(r for r in rows
                    if r["status"] == "achieved")
        rec = record(good)
        (out / "outcome-record.json").write_text(
            json.dumps(rec, indent=2) + "\n")
        closed = next(r for r in rows if r["why"] == "escalated"
                      and r["customer"] == "resolved")
        (out / "case-outcome.json").write_text(
            json.dumps(case_record(closed), indent=2) + "\n")
        (out / "receipt-outcome.json").write_text(json.dumps(
            {"did_what": {"outcome": {
                "status": "pending", "metric": METRIC}}},
            indent=2) + "\n")


if __name__ == "__main__":
    main()
