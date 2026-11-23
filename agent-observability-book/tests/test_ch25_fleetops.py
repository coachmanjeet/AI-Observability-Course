"""Chapter 25: fleet operations."""
import json

from orchestration import fleetops as fo


def test_no_alert_before_minimum_sample():
    _, _, _, table = fo.watch()
    day1 = table[0]
    assert day1[1] < fo.MIN_N and not day1[4]


def test_alert_on_day_two_with_significant_drift():
    _, _, drift, table = fo.watch()
    assert len(table) == 2 and table[-1][4]
    assert drift["refund rate"]["p"] < fo.ALPHA
    assert drift["refund rate"]["new"] > \
        drift["refund rate"]["old"]


def test_two_prop_test_is_sane():
    assert fo.two_prop_p(50, 100, 50, 100) == 1.0
    assert fo.two_prop_p(10, 1000, 90, 1000) < 1e-6


def test_drill_rolls_back_through_registry():
    rows, by, drift, _ = fo.watch()
    fo.drill(rows, by, drift)
    assert fo.TRAFFIC == {fo.OLD: 1.0, fo.NEW: 0.0}
    assert fo.REGISTRY["agent://pronto/speedy@2.4.0"] == \
        "rolled_back"


def test_retired_version_keeps_its_receipts():
    rows, by, _, _ = fo.watch()
    ret = fo.retire(fo.NEW, rows)
    assert ret["state"] == "retired"
    assert ret["receipts_kept"] == len(by[fo.NEW]) > 0
    assert ret["registry_ref"].endswith("speedy@2.4.0")


def test_every_receipt_names_its_version():
    rows, _, _, _ = fo.watch()
    assert {r["who"]["agent_version"] for r in rows} == \
        {"2.3.1", "2.4.0"}
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    assert ex["who"]["agent_version"] == fo.OLD


def test_a_quiet_canary_with_too_little_evidence_extends():
    _, _, _, table = fo.watch(min_n=400)
    assert [d[5] for d in table] == ["extend"] * 3


def test_expand_needs_evidence_and_mature_outcomes():
    assert fo.decide(3, 500, False, False) == "extend"
    assert fo.decide(7, 150, False, False) == "extend"
    assert fo.decide(7, 500, False, False) == "expand"
    assert fo.decide(1, 10, False, True) == "roll back"
