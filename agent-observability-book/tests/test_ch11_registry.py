"""Chapter 11: one registry with owners, tiers and a lifecycle."""
import json

import pytest

from registry.registry import build, review_week, tier


def test_risk_tier_follows_consequence_classes():
    assert tier(["financial", "read_sensitive"]) == "high"
    assert tier(["write"]) == "medium"
    assert tier([]) == "low"


def test_drafts_from_discovery_start_as_drafts():
    reg = build()
    assert reg.records["agent://unregistered/tally"]["state"] == \
        "draft"


def test_a_draft_cannot_jump_to_approved():
    reg = build()
    with pytest.raises(ValueError):
        reg.move("agent://unregistered/tally", "approved", "x", "y",
                 "2027-02-08")


def test_approval_needs_an_owner():
    reg = build()
    tally = "agent://unregistered/tally"
    reg.move(tally, "in_review", "x", "y", "2027-02-08")
    with pytest.raises(ValueError, match="owner"):
        reg.move(tally, "approved", "x", "y", "2027-02-08")


def test_the_week_leaves_no_drafts_and_a_trail():
    reg = build()
    review_week(reg)
    states = {r["state"] for r in reg.records.values()}
    assert "draft" not in states
    assert len(reg.events) == 4


def test_third_party_records_come_from_their_own_cards():
    reg = build()
    ledger = reg.records["agent://payco/ledger"]
    assert ledger["version"] == "4.2.0"
    assert "disputes.open" in ledger["capabilities"]


def test_who_matches_chapter_2_except_attestation():
    # workload_id and identity come from attestation (Ch 12)
    reg = build()
    who = reg.who("agent://pronto/speedy", "pronto-support-runtime")
    ex = json.loads(open("receipts/examples/"
                         "02-speedy-refund-40.json").read())["who"]
    ex.pop("workload_id")
    ex.pop("identity")
    assert who == ex


def test_a_credit_moves_route_to_high_and_needs_a_review():
    from registry.registry import Registry
    assert tier(["write"]) == "medium"
    assert tier(["write", "financial"]) == "high"
    reg = Registry()
    reg.put({"id": "agent://pronto/route", "name": "Route",
             "version": "0.10.0", "owner": "team:logistics",
             "kind": "first_party", "state": "in_review",
             "risk_tier": tier(["write", "financial"])})
    with pytest.raises(ValueError, match="security_review"):
        reg.move("agent://pronto/route", "approved", "platform lead",
                 "credit added", "2027-02-15")
