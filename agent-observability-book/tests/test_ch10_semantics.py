"""Chapter 10: a governed metric beats SQL guessed from a schema."""
from context.semantic import (METRICS, answers, below,
                              compile_metric, fingerprint, load,
                              source)


def test_the_two_answers_disagree_on_two_pairs():
    raw, governed = answers(load())
    assert set(below(raw)) ^ set(below(governed)) == {
        "oat milk -> almond milk",
        "peanut butter -> almond butter"}


def test_test_orders_drag_the_raw_rate_down():
    raw, governed = answers(load())
    pair = "oat milk -> almond milk"
    assert round(raw[pair], 2) == 0.46
    assert governed[pair] == 0.75


def test_big_baskets_inflate_the_raw_rate():
    raw, governed = answers(load())
    pair = "peanut butter -> almond butter"
    assert round(raw[pair], 2) == 0.68
    assert governed[pair] == 0.30


def test_the_metric_counts_each_offer_once():
    db = load()
    sql = compile_metric("substitution_acceptance_rate", "pair")
    assert "order_lines" not in sql
    assert "status = 'delivered'" in sql


def test_the_receipt_source_names_owner_and_version():
    src = source()
    assert src["authority"] == "team:merchandising"
    assert src["version"] == str(
        METRICS["substitution_acceptance_rate"]["version"])
    assert set(src) == {"id", "uri", "version", "retrieved_at",
                        "authority", "sensitivity"}


def test_a_silent_edit_changes_the_fingerprint():
    before = fingerprint()
    m = METRICS["substitution_acceptance_rate"]
    saved = m["where"]
    m["where"] = "1 = 1"
    try:
        assert fingerprint() != before
    finally:
        m["where"] = saved
