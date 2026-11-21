"""Chapter 1: Saturday night, replayed from what Pronto had."""
import json
import pathlib

from incident.replay import age, evidence, payments
from receipts.validate import unanswered

ROOT = pathlib.Path(__file__).parent.parent


def test_two_refunds_in_the_payments_log():
    night = payments()
    assert [p["refund"] for p in night] == ["rf_9931", "rf_9934"]
    assert [p["amount"] for p in night] == ["40.00", "85.00"]


def test_night_owl_used_an_old_personal_token():
    owl = payments()[1]
    assert owl["credential"] == "personal token"
    assert age(owl) == 94


def test_speedy_refund_is_in_its_trace():
    what, rec = evidence()["rf_9931"]
    assert rec["evidence"]["trace_id"].startswith("4bf92f35")
    assert rec["evidence"]["span_id"] == "00f067aa0ba902b7"
    assert "9 spans" in what


def test_both_refunds_answer_two_of_seven():
    found = evidence()
    for ref in ("rf_9931", "rf_9934"):
        assert len(unanswered(found[ref][1])) == 5


def test_the_target_receipt_answers_all_seven():
    path = ROOT / "receipts/examples/02-speedy-refund-40.json"
    assert unanswered(json.loads(path.read_text())) == []
