"""Chapter 21: telemetry joined to business value."""
import json

from metering.traffic import month
from metering.value import (START, by_conversation, outcomes,
                            record, tree)


def run():
    spans, convs = month("tenant:pronto", START, 28)
    per = by_conversation(spans)
    rows = outcomes(convs, per)
    return convs, per, rows, tree(convs, per, rows)


def test_every_first_contact_gets_one_outcome():
    convs, _, rows, t = run()
    firsts = [c for c in convs if not c["follow_up"]]
    assert len(rows) == len(firsts) == t["first"]
    assert t["resolved"] + t["came_back"] + t["escalated"] == \
        t["first"]


def test_timeouts_drive_comebacks():
    _, _, rows, _ = run()
    to = [r for r in rows if r["timeout"]]
    rate_to = sum(r["why"] == "came back" for r in to) / len(to)
    rest = [r for r in rows if not r["timeout"]]
    rate = sum(r["why"] == "came back" for r in rest) / len(rest)
    assert rate_to > 5 * rate


def test_cost_per_conversation_matches_the_receipt():
    _, _, _, t = run()
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    one = float(ex["at_what_cost"]["model_cost"]["value"])
    assert abs(float(t["per_conv"]) - one) < 0.002


def test_model_plus_escalation_cost_counts_people():
    _, _, _, t = run()
    assert t["confirmed_cost"] > 10 * t["per_confirmed"]


def test_escalations_count_only_on_case_evidence():
    _, _, rows, t = run()
    esc = [r for r in rows if r["why"] == "escalated"]
    assert sum(t["esc"].values()) == len(esc) == t["escalated"]
    for r in esc:
        if r["customer"] == "resolved":
            c = r["case"]
            assert c and c["closed_at"] and not c["reopened_at"]
    assert t["esc"]["pending"] and t["esc"]["unknown"]
    assert t["customer"] == t["resolved"] + t["esc"]["resolved"]
    assert t["mature"] == t["first"] - t["pending"]


def test_customer_rule_covers_every_case():
    from datetime import timedelta
    from metering.value import AS_OF, customer
    done = AS_OF - timedelta(days=20)
    assert customer("came back", None) == "not resolved"
    assert customer("escalated", None) == "unknown"
    assert customer("escalated", {"closed_at": None,
                                  "reopened_at": None}) == "pending"
    assert customer("escalated", {"closed_at": done,
                                  "reopened_at": done}) == \
        "not resolved"
    assert customer("escalated", {"closed_at": AS_OF,
                                  "reopened_at": None}) == "pending"
    assert customer("escalated", {"closed_at": done,
                                  "reopened_at": None}) == "resolved"
    late = done + timedelta(days=9)          # after its 7 days
    assert customer("escalated", {"closed_at": done,
                                  "reopened_at": late}) == "resolved"


def test_trace_retention_changes_the_sample_not_the_totals():
    from metering.value import retention
    spans, convs = month("tenant:pronto", START, 28)
    per = by_conversation(spans)
    rows = outcomes(convs, per)
    t = tree(convs, per, rows)
    r = retention(spans, convs, rows, keep=0.30)
    assert r["stored"] < 0.35 * r["all"]
    assert r["traces_cost"] * 10 < 4 * r["usage_cost"]
    assert r["usage_cost"] == t["cost"]
    assert r["confirmed_cost"] == t["confirmed_cost"]
    full = retention(spans, convs, rows, keep=1.0)
    assert full["traces_cost"] == full["usage_cost"] == t["cost"]


def test_redelivered_usage_records_count_once():
    from metering.value import dedupe, usage_records
    spans, _ = month("tenant:pronto", START, 28)
    raw = usage_records(spans)
    once = dedupe(raw)
    assert len(raw) > len(once)
    assert len(once) == len(usage_records(spans, redelivered=0))


def test_usage_key_is_tenant_trace_and_span():
    from decimal import Decimal
    from metering.value import dedupe
    rec = {"tenant": "tenant:pronto", "trace_id": "a" * 32,
           "span_id": "00f067aa0ba902b7", "cost": Decimal("0.01")}
    resent = dict(rec)
    other_trace = {**rec, "trace_id": "b" * 32}
    other_tenant = {**rec, "tenant": "tenant:hilltop"}
    kept = dedupe([rec, resent, other_trace, other_tenant])
    assert len(kept) == 3      # the resend once; the others both


def test_outcome_record_matches_example_3():
    _, _, rows, _ = run()
    rec = record(next(r for r in rows
                      if r["status"] == "achieved"))
    ex = json.load(open("receipts/examples/"
                        "03-outcome-refund-40.json"))
    for k in ("record_type", "status", "metric"):
        assert rec[k] == ex[k]
    assert rec["evidence"]["evaluation"] == \
        ex["evidence"]["evaluation"]


def test_receipt_outcome_starts_pending():
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    assert ex["did_what"]["outcome"]["status"] == "pending"
    assert ex["did_what"]["outcome"]["metric"] == \
        "resolved_without_escalation_within_7d"


def test_comebacks_add_up_by_cause():
    from collections import Counter
    from metering.traffic import month
    from metering.value import START, by_conversation, outcomes
    spans, convs = month("tenant:pronto", START, 28)
    per = by_conversation(spans)
    back = [r for r in outcomes(convs, per)
            if r["why"] == "came back"]
    last = Counter(per[r["conversation_id"]]["tools"][-1]
                   for r in back if not r["timeout"])
    assert len(back) == 163
    assert sum(r["timeout"] for r in back) == 26
    assert last == {"orders.get": 83, "photos.verify": 41,
                    "refunds.create": 13}


def test_case_outcome_records_fit_the_outcome_schema():
    import jsonschema
    from metering.value import case_record
    schema = json.load(open("receipts/agent-outcome.schema.json"))
    envelope = {"receipt_version": "0.1",
                "receipt_id": "rcpt_0123456789AB",
                "integrity": {"canonicalization": "JCS-RFC8785",
                              "prev_hash": "sha256:" + "0" * 64,
                              "hash": "sha256:" + "1" * 64}}
    _, _, rows, _ = run()
    seen = set()
    for r in rows:
        if r["why"] == "escalated" and r["customer"] != "pending":
            rec = case_record(r)
            jsonschema.validate({**rec, **envelope}, schema)
            seen.add(rec["status"])
    assert seen == {"achieved", "not_achieved", "unknown"}
