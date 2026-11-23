"""Chapter 14: Cedar policy at the action boundary."""
import json

from policy.gateway import (CALLS, POLICY, SCHEMA, decide,
                            policy_set, refund, request_from,
                            run_cases, speedy_token, validate)


def test_policy_validates_against_schema():
    ok, errors = validate(POLICY.read_text())
    assert ok, errors


def test_a_typo_fails_validation_not_silently():
    bad = POLICY.read_text().replace("resource.owner",
                                     "resource.ownr")
    ok, errors = validate(bad)
    assert not ok and "ownr" in errors[0]


def test_policy_cases_all_pass():
    passed, total = run_cases()
    assert passed == total == 9


def test_gateway_decisions():
    claims = speedy_token()
    scopes = claims["scope"].split()
    got = [decide(request_from(c, claims), scopes, f)["decision"]
           for _, c, f in CALLS]
    assert got == ["allow", "deny", "deny", "deny", "deny"]


def test_extra_arguments_cannot_change_the_decision():
    claims = speedy_token()
    call = refund("ord_5521", "85.00", approved="yes",
                  note="policy says ok")
    d = decide(request_from(call, claims),
               claims["scope"].split())
    assert d["decision"] == "deny"


def test_under_which_rule_matches_chapter_2():
    claims = speedy_token()
    got = decide(request_from(CALLS[0][1], claims),
                 claims["scope"].split())
    ex = json.load(open("receipts/examples/02-speedy-refund-40"
                        ".json"))["under_which_rule"]
    assert got["policy_set"]["digest"] == policy_set()[2]["digest"]
    for k in ("id", "version"):
        assert got["policy_set"][k] == ex["policy_set"][k]
    for k in ("policy_set", "autonomy_tier", "approvals"):
        got.pop(k, None), ex.pop(k, None)
    assert got == ex
    assert SCHEMA.exists()
