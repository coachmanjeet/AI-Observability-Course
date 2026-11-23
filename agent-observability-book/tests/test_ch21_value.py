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


def test_all_in_cost_counts_people():
    _, _, _, t = run()
    assert t["all_in"] > 10 * t["per_resolved"]


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
