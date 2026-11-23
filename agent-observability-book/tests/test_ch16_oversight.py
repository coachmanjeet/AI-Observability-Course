"""Chapter 16: autonomy tiers, approvals and responses."""
import json

from policy.gateway import POLICY, validate
from policy.oversight import (V4, approve, refund_with, respond,
                              sampled, tier_for)


def test_tiers_follow_the_ladder():
    assert tier_for("8.00")["tier"] == "act_autonomously"
    assert tier_for("10.00")["tier"] == "act_autonomously"
    assert tier_for("40.00")["tier"] == "act_with_sampled_review"
    assert tier_for("85.00")["tier"] == "act_with_approval"
    assert tier_for("900.00")["tier"] == "suggest_only"


def test_sampling_is_deterministic_and_near_rate():
    ids = [f"rcpt_speedy_{i:04d}" for i in range(2000)]
    n = sum(sampled(i, 5) for i in ids)
    assert 70 <= n <= 130
    assert [sampled(i, 5) for i in ids[:50]] == \
        [sampled(i, 5) for i in ids[:50]]


def test_approval_is_bound_to_order_and_amount():
    c = {"amount": "85.00", "photo": True, "refunds_30d": 0}
    ok, _ = approve("ord_5602", "85.00", c, "emp_2210")
    assert refund_with("ord_5602", "85.00", ok)["decision"] == \
        "allow_with_approval"
    assert refund_with("ord_5602", "95.00", ok)["decision"] == \
        "deny"
    assert refund_with("ord_5521", "85.00", ok)["decision"] == \
        "deny"


def test_summary_that_disagrees_with_facts_is_refused():
    lie = {"amount": "400.00", "photo": True, "refunds_30d": 0}
    ok, why = approve("ord_5640", "400.00", lie, "emp_2210")
    assert ok is None and why == "rejected: 3 claims disagree"


def test_graduated_responses():
    assert respond("monitor").endswith("sampled for review")
    assert respond("restrict") == "held for approval"
    assert respond("pause").endswith("registered-agents-only")
    assert respond("revoke") == "no identity issued"
    assert respond("pause") != respond("monitor")


def test_v4_validates_and_receipt_fields_match_chapter_2():
    assert validate(V4[0].read_text())[0]
    assert validate(POLICY.read_text())[0]
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    rule = ex["under_which_rule"]
    assert tier_for("40.00")["tier"] == rule["autonomy_tier"]
    assert rule["approvals"] == []
