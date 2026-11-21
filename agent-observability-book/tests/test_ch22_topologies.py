"""Chapter 22: orchestration topologies and governance cost."""
import json

from orchestration.score import rows


def by_name():
    return {r["topology"]: r for r in rows()}


def test_router_has_no_model_routing():
    r = by_name()
    assert r["router"]["model_routes"] == 0
    assert r["supervisor"]["model_routes"] == 2


def test_broker_widens_reach_to_other_owners():
    r = by_name()
    assert r["router"]["reach"] == 4
    assert r["broker"]["reach"] == 7
    assert "promo-co" in r["broker"]["outside"]
    assert r["router"]["outside"] == ["payco"]


def test_broker_loses_the_customer_unless_it_forwards():
    r = by_name()
    assert r["broker"]["named"] == "4/7"
    assert r["broker+ctx"]["named"] == "7/7"
    ledger = [x for x in r["broker"]["receipts"]
              if x["who"]["agent_id"] == "Ledger"]
    assert {x["for_whom"]["principal_id"] for x in ledger} == \
        {"agent://pronto/broker"}


def test_receipts_link_to_the_hop_that_caused_them():
    rec = by_name()["handoff"]["receipts"]
    handoff = next(x for x in rec
                   if x["did_what"]["action"]["tool"]
                   == "agent:Ledger")
    ledger = [x for x in rec if x["who"]["agent_id"] == "Ledger"]
    assert all(x["evidence"]["parent_receipt_id"]
               == handoff["receipt_id"] for x in ledger)


def test_one_ungated_call_in_every_topology():
    assert {r["gated"] for r in rows()} == {"4/5"}


def test_refund_via_matches_chapter_2():
    rec = by_name()["router"]["receipts"]
    refund = next(x for x in rec
                  if x["did_what"]["action"]["tool"]
                  == "refunds.create")
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    assert refund["did_what"]["action"]["via"] == \
        ex["did_what"]["action"]["via"]
