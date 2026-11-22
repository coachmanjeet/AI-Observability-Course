"""Chapter 29: pricing models on the same usage."""
import json

import pytest

from metering.pricing import MODELS, PILOTS, simulate


@pytest.fixture(scope="module")
def sim():
    return simulate()


def test_six_models_three_tenants(sim):
    _, _, out = sim
    assert len(MODELS) == 6
    assert all(set(r["bills"]) == set(PILOTS)
               for r in out.values())


def test_bad_month_lowers_outcome_bills(sim):
    _, _, out = sim
    assert out["per outcome"]["bad_month"] < 0
    assert out["base + outcome"]["bad_month"] < 0


def test_per_conversation_charges_more_for_worse_service(sim):
    _, _, out = sim
    assert out["per conversation"]["bad_month"] > 0


def test_seats_ignore_the_work(sim):
    _, _, out = sim
    assert out["per seat"]["bad_month"] == 0


def test_every_model_covers_cost(sim):
    _, _, out = sim
    assert all(r["margin"] > 0.5 for r in out.values())


def test_outcome_meter_matches_chapter_2():
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    assert ex["at_what_cost"]["billable"][0]["meter"] == \
        "resolved_conversation"
