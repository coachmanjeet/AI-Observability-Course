"""Chapter 18: least privilege and authorization drift."""
import json

from policy.privilege import RISKY, covers, review, task_scopes


def test_scope_hierarchy():
    assert covers("refunds:create:any", "refunds:create:max_50")
    assert covers("refunds:create:max_100", "refunds:create:max_50")
    assert not covers("refunds:create:max_50",
                      "refunds:create:max_100")
    assert covers("orders:read:any", "orders:read:own")
    assert not covers("orders:read:own", "orders:read:any")


def test_unused_risky_grants_are_found():
    rep = review()
    assert set(rep["speedy"]["risky_unused"]) == {
        "refunds:create:any", "customers:write:any"}
    risky = sum(len(r["risky_unused"]) for r in rep.values())
    assert risky == 6


def test_drift_since_last_review():
    rep = review()
    assert rep["coder"]["drift"] == ["ci:secrets:read"]
    assert rep["promo"]["drift"] == ["customers:read:phone"]
    assert rep["speedy"]["drift"] == []


def test_proposal_keeps_used_and_needed_only():
    sp = review()["speedy"]
    assert sp["keep"] == ["orders:read:own",
                          "refunds:create:max_50"]
    assert sp["add"] == ["customers:write:own"]
    assert not set(sp["remove"]) & set(sp["keep"])
    assert all(s not in RISKY for s in sp["keep"] + sp["add"])


def test_task_tokens_are_smaller_than_grants():
    assert task_scopes("speedy", "order_status") == \
        ["orders:read:own"]


def test_refund_scopes_match_chapter_2():
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    assert task_scopes("speedy", "refund_damaged") == \
        ex["for_whom"]["scopes"]
