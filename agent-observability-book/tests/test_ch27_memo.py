"""Chapter 27: the funding memo adds up, and keeps cash apart."""
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
