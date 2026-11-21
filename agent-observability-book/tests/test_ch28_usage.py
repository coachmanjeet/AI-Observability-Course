"""Chapter 28: metering agent work."""
import json
from collections import Counter

import pytest

from metering.usage import RATE, dedupe, invoice, run


@pytest.fixture(scope="module")
def res():
    return run()


def test_duplicates_are_removed_by_key(res):
    for r in res.values():
        assert r["dupes"] > 0
        keys = Counter((e["idempotency_key"], e["status"])
                       for e in r["kept"])
        assert max(keys.values()) == 1
        again, n = dedupe(r["kept"] + r["kept"])
        assert n == len(r["kept"]) and again == r["kept"]


def test_every_first_contact_has_one_pending_event(res):
    for r in res.values():
        pending = [e for e in r["kept"]
                   if e["status"] == "pending_outcome"]
        assert len(pending) == r["convs"]
        assert all(e["quantity"] == 0 for e in pending)


def test_billing_waits_for_the_outcome(res):
    for r in res.values():
        for e in r["kept"]:
            if e["status"] == "billed":
                assert e["at"].date().isoformat() > \
                    e["service_date"]


def test_late_outcomes_move_to_the_next_invoice(res):
    inv = res["tenant:hilltop"]["invoice"]
    assert inv["late"] > 0
    assert inv["amount"] == inv["quantity"] * RATE


def test_credits_reduce_the_invoice(res):
    inv = invoice(res["tenant:bayside"]["kept"])
    assert inv["lines"]["credited"] > 0
    assert inv["quantity"] == \
        inv["lines"]["billed"] - inv["lines"]["credited"]


def test_billable_shape_matches_chapter_2():
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    b = ex["at_what_cost"]["billable"][0]
    assert b["meter"] == "resolved_conversation"
    assert b["status"] == "pending_outcome" and \
        b["quantity"] == 0
    assert b["idempotency_key"].endswith(":resolved")
