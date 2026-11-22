"""Chapter 32: data residency."""
import json

from comply.residency import (allowed, conversation, pick_model,
                              where)


def test_personal_data_stays_in_residency():
    assert allowed("tenant:fresca", "eu-central-1", "personal")
    assert not allowed("tenant:fresca", "us-west-2", "personal")
    assert not allowed("tenant:fresca", "us-west-2", "metadata")


def test_public_data_may_travel():
    assert allowed("tenant:fresca", "us-west-2", "public")


def test_failover_stays_in_region():
    assert pick_model("tenant:fresca") == "eu-west-1"
    assert pick_model("tenant:fresca",
                      ("eu-west-1",)) == "eu-central-1"
    assert pick_model("tenant:fresca",
                      ("eu-west-1", "eu-central-1")) is None


def test_violating_hops_are_blocked():
    _, rows = conversation("tenant:fresca", ("eu-west-1",))
    blocked = [r[0] for r in rows if r[3] == "blocked"]
    assert blocked == ["analytics copy"]


def test_us_tenant_unaffected():
    _, rows = conversation("tenant:pronto")
    model = rows[0][1]
    assert model == "us-west-2"


def test_where_matches_chapter_2():
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))["where"]
    model = pick_model("tenant:pronto")
    assert where("tenant:pronto", model, "us-west-2") == ex
