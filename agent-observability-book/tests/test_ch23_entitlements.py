"""Chapter 23: entitlements and FinOps."""
import json

from metering.entitlements import (DAILY_BUDGET, Runtime,
                                   billing_account, runaway)


def test_plan_limits_agents_and_models():
    rt = Runtime()
    assert rt.start("tenant:corner", "route").startswith("denied")
    assert rt.start("tenant:corner", "speedy",
                    "standard").startswith("denied")
    assert rt.start("tenant:corner", "speedy", "small") == "ok"
    assert rt.start("tenant:bayside", "route") == "ok"


def test_quota_is_enforced():
    rt = Runtime()
    rt.used["tenant:hilltop"] = 2000
    assert rt.start("tenant:hilltop") == \
        "denied: monthly quota reached"


def test_alerts_fire_once_in_order():
    rt, _, _ = runaway()
    msgs = [m for _, m in rt.log]
    assert msgs == ["alert 50% of daily budget",
                    "alert 80% of daily budget",
                    "kill switch: new conversations paused"]


def test_kill_switch_stops_spend_at_budget():
    rt, results, _ = runaway()
    assert rt.spend["tenant:bayside"] <= \
        DAILY_BUDGET["tenant:bayside"]
    assert results[-1] == "denied: budget kill switch"
    assert results.count("ok") < len(results) / 2


def test_other_tenants_are_unaffected():
    _, _, other = runaway()
    assert other == "ok"


def test_billing_account_matches_chapter_2():
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    assert billing_account("tenant:pronto")["at_what_cost"] == \
        {"billing_account":
         ex["at_what_cost"]["billing_account"]}


def test_the_cap_cuts_a_charge_to_the_headroom():
    from decimal import Decimal as D
    from metering.entitlements import cap_charge, cap_example
    assert cap_charge(D("249.90"), D("0.25"), D("250")) == \
        (D("0.10"), D("0.15"))
    assert cap_charge(D("250"), D("0.25"), D("250")) == \
        (D("0"), D("0.25"))
    cap, jul, aug = cap_example()
    assert aug == (D("0.25"), D("0"))    # next month's own cap
