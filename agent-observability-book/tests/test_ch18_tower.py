"""Chapter 18: the control tower's fleet view."""
from orchestration.tower import HERE, gaps, load, tower


def run():
    return tower(load(HERE / "fleet-2027-03-29.json"),
                 load(HERE.parent / "maturity" / "fleet.json"))


def test_estate_moved_from_l1_to_l3():
    rows, now, then = run()
    assert then["estate"] == 1 and then["weakest"] == ["Night Owl"]
    assert now["estate"] == 3 and now["weakest"] == ["Promo"]


def test_answers_follow_conformance():
    rows, _, _ = run()
    by = {r["agent"]: r for r in rows}
    assert by["Speedy"]["answered"] == 100
    assert by["Ledger"]["answered"] == 71      # 5 of 7
    assert by["Promo"]["answered"] == 29       # 2 of 7


def test_third_party_cost_is_unknown_not_zero():
    rows, _, _ = run()
    by = {r["agent"]: r for r in rows}
    assert by["Ledger"]["cost_per_action"] == "n/a"
    assert by["Speedy"]["cost_per_action"] == "$0.015"


def test_gaps_name_owners_work():
    rows, _, _ = run()
    agents = [a for a, _ in gaps(rows)]
    assert agents == ["Pick", "Ledger", "Promo"]


def test_night_owl_is_retired_not_hidden():
    fleet = load(HERE / "fleet-2027-03-29.json")
    names = [r["name"] for r in fleet["retired"]]
    assert names == ["Night Owl", "Tally"]
    assert "Night Owl" not in [a["name"]
                               for a in fleet["agents"]]


def test_every_agent_has_an_owner():
    fleet = load(HERE / "fleet-2027-03-29.json")
    assert all(a["owner"].startswith("team:")
               for a in fleet["agents"])


def test_exact_coverage_is_not_rounded():
    rows, _, _ = run()
    by = {r["agent"]: r for r in rows}
    assert by["Pick"]["answered"] == 99
    assert by["Pick"]["answered_exact"] == 98.57
    assert by["Pick"]["r4_share"] == 98.0
