"""Chapter 19: the gateway is the only path."""
from policy.boundary import run

ROWS = {label: (outcome, why) for label, outcome, why in run()}


def test_only_gateway_tokens_reach_the_refund_service():
    assert ROWS["via gateway, $40"][0] == "allow"
    assert ROWS["direct, Speedy's own token"][0] == "reject"
    assert ROWS["gateway token, other order"][0] == "reject"


def test_consequential_calls_fail_closed():
    assert ROWS["engine down, refund $40"] == ("deny",
                                               "fail closed")
    assert ROWS["engine down, orders.get"][0] == "deny"
    assert ROWS["engine down, catalog.search"][0] == "allow"


def test_policy_change_invalidates_the_cache():
    assert ROWS["same call 20 s later"][1] == "cached"
    assert ROWS["after policy v3 -> v4"][1] == \
        "decided again"


def test_a_freeze_beats_a_cached_allow():
    assert ROWS["payments freeze on"][0] == "deny"
