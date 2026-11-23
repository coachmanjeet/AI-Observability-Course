"""Chapter 21: the funding memo adds up, and keeps cash apart."""
import math

from metering import memo

M = memo.memo()


def test_spend_lines_add_to_total():
    assert sum(M["spend"].values()) == M["total"]


def test_capacity_is_not_cash():
    assert M["released"] == M["first"] - 137
    assert memo.CASH_SAVED == 0
    assert M["released_usd"] > M["total"]


def test_break_even_covers_total_spend():
    be = M["break_even"]
    assert be == math.ceil(M["total"] / memo.HUMAN_PER_CONTACT)
    assert (be - 1) * memo.HUMAN_PER_CONTACT < M["total"]


def test_both_arms_share_one_customer_outcome():
    assert M["customer"] == M["first"] - 163
    assert M["customer"] > M["resolved"]      # escalations count


def test_gate_has_three_answers():
    assert memo.gate(940, 1000, 940, 1000)[0] == \
        "insufficient evidence"
    assert memo.gate(4210, 4480, 1053, 1120)[0] == "fund"
    assert memo.gate(3900, 4480, 1053, 1120)[0] == "stop"


def test_one_month_at_ten_percent_cannot_settle_two_points():
    a, b = M["precision"]
    assert a > float(memo.TOLERANCE) * 100
    assert b < float(memo.TOLERANCE) * 100


def test_fully_loaded_cost_includes_every_line():
    people = memo.HUMAN_PER_CONTACT * 137
    assert M["loaded"] == (M["total"] + people) / M["resolved"]
    assert round(M["loaded"], 2) == memo.D("2.24")
