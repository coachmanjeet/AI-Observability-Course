"""What the control plane costs to build and run (Chapter 3).

Usage: python -m maturity.funding

A planning model, not a benchmark. Team sizes, loaded cost and
infrastructure are inputs in funding.yaml; change them to your
own and the totals follow. The point it makes holds for most
inputs: the control plane is mostly people, and most of it is
a fixed cost, so the cost per agent falls as the estate grows.
"""
import pathlib

import yaml

HERE = pathlib.Path(__file__).parent
YEARS = 3          # the horizon a funding request is judged on


def load():
    return yaml.safe_load((HERE / "funding.yaml").read_text())


def cost(estate, m):
    fte = m["loaded_cost_per_fte"]
    build_fte = sum(estate["build"].values())
    run_fte = sum(estate["run"].values())
    build = build_fte * fte * estate["build_months"] / 12
    infra = m["infra_per_agent_year"] * estate["agents"]
    run = run_fte * fte + infra
    return {"agents": estate["agents"],
            "build_months": estate["build_months"],
            "build_fte": build_fte, "build": build,
            "run_fte": run_fte, "infra": infra, "run": run,
            "per_agent": run / estate["agents"],
            # a CFO's view: build once, run for YEARS
            "three_year": build + YEARS * run,
            "per_agent_year": (build + YEARS * run)
            / (YEARS * estate["agents"])}


def main():
    m = load()
    rows = {n: cost(e, m) for n, e in m["estates"].items()}
    print("Control plane cost: Pronto's planning model")
    print(f"{'':<24}{'7 agents':>12}{'70 agents':>12}")
    a, b = rows["pronto"], rows["large"]
    for key, label, fmt in (
            ("build_months", "build, months", "{:,.0f}"),
            ("build_fte", "build team, FTE", "{:,.1f}"),
            ("build", "build cost", "${:,.0f}"),
            ("run_fte", "run team, FTE", "{:,.2f}"),
            ("infra", "infrastructure a year", "${:,.0f}"),
            ("run", "run cost a year", "${:,.0f}"),
            ("per_agent", "run cost per agent", "${:,.0f}"),
            ("three_year", "three years, all in", "${:,.0f}"),
            ("per_agent_year", "  per agent a year", "${:,.0f}")):
        print(f"{label:<24}{fmt.format(a[key]):>12}"
              f"{fmt.format(b[key]):>12}")


if __name__ == "__main__":
    main()
