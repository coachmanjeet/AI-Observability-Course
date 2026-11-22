"""Chapter 3: the control plane's planning model."""
from maturity.funding import cost, load


def test_cost_per_agent_falls_with_scale():
    m = load()
    small = cost(m["estates"]["pronto"], m)
    large = cost(m["estates"]["large"], m)
    assert small["build"] == 375000
    assert large["per_agent"] < small["per_agent"] / 2


def test_people_dominate_the_run_cost():
    m = load()
    for e in m["estates"].values():
        c = cost(e, m)
        assert c["infra"] < 0.1 * c["run"]
