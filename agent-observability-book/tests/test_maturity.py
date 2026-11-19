"""Chapter 3: the five-level maturity self-assessment."""
import copy
import json
import pathlib

import pytest

from maturity.assess import assess, main, score

FLEET_PATH = pathlib.Path(__file__).parent.parent / "maturity" / "fleet.json"
FLEET = json.loads(FLEET_PATH.read_text(encoding="utf-8"))


def agent(name, fleet=FLEET):
    return next(a for a in fleet["agents"] if a["name"] == name)


@pytest.mark.parametrize("name, level", [
    ("Speedy", 4), ("Pick", 3), ("Route", 3), ("Coder", 2),
    ("Ledger", 3), ("Promo", 2), ("Night Owl", 1),
])
def test_each_agent_lands_on_its_rung(name, level):
    assert score(agent(name))[0] == level


def test_next_step_is_the_first_failed_check():
    assert "borrowed credential" in score(agent("Coder"))[1]
    assert "in the prompt" in score(agent("Pick"))[1]
    assert "0 of 1,184" in score(agent("Speedy"))[1]


def test_estate_is_as_mature_as_its_weakest_agent():
    result = assess(FLEET)
    assert result["estate"] == 1 and result["weakest"] == ["Night Owl"]
    assert result["pillars"] == {"Discover": 5, "Govern": 2, "Observe": 0}


def test_shutting_off_night_owl_raises_the_floor_to_two():
    fleet = copy.deepcopy(FLEET)
    fleet["agents"] = [a for a in fleet["agents"] if a["kind"] != "shadow"]
    result = assess(fleet)
    assert result["estate"] == 2 and result["weakest"] == ["Coder", "Promo"]


def test_level_five_needs_a_receipt_for_every_action():
    speedy = copy.deepcopy(agent("Speedy"))
    speedy["r4_receipts_7d"] = speedy["actions_7d"] - 1
    assert score(speedy)[0] == 4                      # one gap is a gap
    speedy["r4_receipts_7d"] = speedy["actions_7d"]
    assert score(speedy)[0] == 5


def test_rungs_cannot_be_skipped():
    owl = copy.deepcopy(agent("Night Owl"))
    owl.update(policy="outside_model", traced=True,
               r4_receipts_7d=owl["actions_7d"])
    assert score(owl)[0] == 1                         # receipts without a registry


def test_fail_below_turns_the_score_into_a_gate(capsys):
    assert main([str(FLEET_PATH)]) == 0
    assert main([str(FLEET_PATH), "--fail-below", "2"]) == 1
    assert "Estate level: L1 Invisible, set by Night Owl" in capsys.readouterr().out
