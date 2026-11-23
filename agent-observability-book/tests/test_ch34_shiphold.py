"""Chapter 34: the full receipt and the launch review."""
import pytest

from receipts.validate import RECEIPT, unanswered
from shiphold.review import (BUILD, assemble, gates, plan,
                             signature_ok)
from audit.keys import lab_key

pytestmark = pytest.mark.skipif(
    not (BUILD / "residency" / "where-pronto.json").exists(),
    reason="run make shiphold first")


def test_full_receipt_is_valid_and_complete():
    rec, _, _ = assemble()
    assert not list(RECEIPT.iter_errors(rec))
    assert unanswered(rec) == []


def test_every_field_is_tagged_with_a_chapter():
    rec, tags, _ = assemble()
    assert tags["who.workload_id"] == 16
    assert tags["under_which_rule.autonomy_tier"] == 21
    assert tags["where.region"] == 32
    assert tags["integrity.signature"] == 8


def test_real_values_replace_targets():
    _, _, real = assemble()
    assert real == ["for_whom.token_ref",
                    "knowing_what.context_pack.digest",
                    "under_which_rule.policy_set.digest"]


def test_signature_verifies():
    rec, _, _ = assemble()
    i = rec["integrity"]
    assert signature_ok(lab_key().public_key(),
                        i["signature"], i["hash"])


def test_review_holds_only_low_receipt_agents():
    rec, _, _ = assemble()
    results, held = gates(rec)
    assert len(results) == 14
    assert held == ["Ledger", "Promo"]
    holds = [r[0] for r in results if r[2] == "hold"]
    assert holds == ["R4 coverage"]


def test_every_finding_gets_a_dated_owner():
    rec, _, _ = assemble()
    results, _ = gates(rec)
    items = plan(results)
    assert items[-1][0] == 90
    assert all(owner.startswith("team:")
               for _, _, owner in items)
    assert any("A.5.2" in what for _, what, _ in items)


def test_rounding_cannot_ship_pick_without_an_exception():
    from shiphold.review import exceptions
    rows, live = exceptions()
    assert ("R4 coverage", "Pick") in live
    rec, _, _ = assemble()
    results, held = gates(rec)
    assert "Pick" not in held
    status = {r[0]: r[2] for r in results}
    assert status["evidence pack"] == "excepted"
    assert status["fleet snapshot"] == "pass"


def test_a_lapsed_exception_is_kept_as_history():
    import datetime
    from shiphold.review import exceptions
    rows, live = exceptions(datetime.date(2028, 1, 9))
    assert ("evidence pack", None) not in live
    assert [e["id"] for e in rows].count("EX-2") == 2
