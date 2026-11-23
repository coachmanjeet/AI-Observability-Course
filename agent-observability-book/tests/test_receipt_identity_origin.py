"""Appendix A: an R4 receipt says whether `who` was verified, and
who wrote each source it read."""
import copy
import json
import pathlib

from receipts.validate import _validator

EX = pathlib.Path("receipts/examples")
REFUND = json.loads((EX / "02-speedy-refund-40.json").read_text())
SCHEMA = _validator("agent-receipt.schema.json")


def errors(rec):
    return list(SCHEMA.iter_errors(rec))


def test_example_refund_is_verified_and_sourced():
    assert not errors(REFUND)
    assert REFUND["who"]["identity"] == "verified"
    photo = REFUND["knowing_what"]["sources"][2]
    assert (photo["origin"], photo["trust"]) == \
        ("customer", "evidence")


def test_r4_without_identity_is_invalid():
    rec = copy.deepcopy(REFUND)
    del rec["who"]["identity"]
    assert errors(rec)


def test_verified_needs_a_workload_id():
    rec = copy.deepcopy(REFUND)
    del rec["who"]["workload_id"]
    assert errors(rec)
    rec["who"]["identity"] = "claimed"
    assert not errors(rec)


def test_r4_source_without_origin_is_invalid():
    rec = copy.deepcopy(REFUND)
    del rec["knowing_what"]["sources"][0]["origin"]
    assert errors(rec)


def test_night_owl_is_claimed():
    owl = json.loads(
        (EX / "04-night-owl-refund-85-R1.json").read_text())
    assert owl["who"]["identity"] == "claimed"
    assert not errors(owl)
