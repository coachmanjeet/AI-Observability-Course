"""A one-page funding memo for Speedy's next quarter (Ch 21).

Usage: python -m metering.memo

Takes February's driver tree (metering.value) and the control
plane's planning model (maturity/funding.yaml) and writes the
page finance asks for: the cohort, the quality guardrail, every
monthly cost Speedy adds, the people's time it releases, the
cash it saves, and the break-even volume.

Capacity released is not cash. It turns into cash only when
staffing or spend actually changes, so the memo keeps the two
on separate lines and reports cash saved as zero until then.

Quality is compared on one customer outcome that both arms can
have: the issue stayed resolved for its window, whoever handled
it. Autonomy (resolved without a person) is Speedy's own measure
and is reported apart. The gate has three answers, and
"insufficient evidence" is one of them.
"""
import math
from decimal import Decimal as D

import yaml

from maturity.funding import HERE as FUNDING_DIR
from metering.traffic import month
from metering.value import (HUMAN_PER_CONTACT, START,
                            by_conversation, outcomes, tree)
from orchestration.fleetops import diff_interval

SAMPLE = D("0.05")        # sampled review share (policy/tiers)
CASH_SAVED = D("0")       # no staffing change agreed yet
TOLERANCE = D("0.02")     # Speedy may trail people by 2 pts
HOLDOUT, MONTHS = D("0.20"), 2   # May and June, to people
NEXT_REVIEW = "Jul 19, 2027"


def gate(k_ai, n_ai, k_people, n_people, tol=float(TOLERANCE)):
    """Fund, stop, or insufficient evidence, from Speedy minus
    people on the customer outcome, with a 95% interval."""
    iv = diff_interval(k_ai, n_ai, k_people, n_people)
    _, low, high = iv
    if low >= -tol:
        return "fund", iv
    if high < -tol:
        return "stop", iv
    return "insufficient evidence", iv


def half_width(rate, first, share, months):
    """The interval's half-width at equal rates, in points."""
    n_people = round(first * share * months)
    n_ai = round(first * (1 - share) * months)
    se = math.sqrt(rate * (1 - rate) * (1 / n_people + 1 / n_ai))
    return 100 * 1.96 * se


def plane_share():
    """Speedy's monthly share of the control plane's cost."""
    model = yaml.safe_load(
        (FUNDING_DIR / "funding.yaml").read_text())
    est = model["estates"]["pronto"]
    fte = sum(est["run"].values())
    year = (D(str(fte)) * model["loaded_cost_per_fte"]
            + model["infra_per_agent_year"] * est["agents"])
    return (year / est["agents"] / 12).quantize(D("0.01")), \
        est["agents"]


def memo():
    spans, convs = month("tenant:pronto", START, 28)
    per = by_conversation(spans)
    t = tree(convs, per, outcomes(convs, per))
    reviews = round(SAMPLE * t["refunds"])
    share, agents = plane_share()
    spend = {
        "model": t["cost"].quantize(D("0.01")),
        f"sampled reviews, {reviews}": (HUMAN_PER_CONTACT
                                        * reviews),
        "control plane share": share,
    }
    total = sum(spend.values())
    released = t["first"] - t["escalated"]
    rate = t["customer"] / t["first"]
    loaded = (total + t["people"]) / t["resolved"]
    return {
        "first": t["first"], "resolved": t["resolved"],
        "customer": t["customer"], "rate": rate,
        "model_people": t["model_people"], "loaded": loaded,
        "precision": [half_width(rate, t["first"], D("0.10"), 1),
                      half_width(rate, t["first"], HOLDOUT,
                                 MONTHS)],
        "holdout": round(t["first"] * HOLDOUT),
        "spend": spend, "total": total, "agents": agents,
        "released": released,
        "released_usd": HUMAN_PER_CONTACT * released,
        "break_even": math.ceil(total / HUMAN_PER_CONTACT),
    }


def show(m):
    auto = 100 * m["resolved"] / m["first"]
    a, b = m["precision"]
    tol = 100 * TOLERANCE
    lines = [
        "Funding memo: Speedy, Pronto tenant, Q2 2027",
        f"cohort      {m['first']:,} first contacts, Feb 2027",
        "outcome     issue resolved within window, any handler",
        f"            Speedy {100 * m['rate']:.1f}%; people: "
        "measured from May",
        f"autonomy    no person involved {auto:.1f}%, "
        "reported apart",
        f"holdout     {HOLDOUT:.0%} of first contacts to people, "
        "May and June",
        f"gate        {NEXT_REVIEW}: Speedy minus people, 95% "
        "interval",
        f"  fund      low end at or above -{tol:.0f} pts",
        f"  stop      high end below -{tol:.0f} pts",
        "  otherwise insufficient evidence: hold scope, "
        "keep holdout",
        f"  width     10% for a month +/-{a:.1f} pts; "
        f"{HOLDOUT:.0%} for {MONTHS} months +/-{b:.1f}",
        "spend a month, USD",
    ]
    for k, v in m["spend"].items():
        lines.append(f"  {k:<24}{v:>11,.2f}")
    lines.append(f"  {'total':<24}{m['total']:>11,.2f}")
    lines += [
        f"per resolved  model + escalation ${m['model_people']:.3f}"
        f"; all lines ${m['loaded']:.2f}",
        f"capacity    {m['released']:,} contacts, "
        f"${m['released_usd']:,.2f} of people's time",
        f"            less {m['holdout']:,} a month to the holdout",
        f"cash saved  ${CASH_SAVED:.2f} until staffing changes",
        f"break-even  {m['break_even']:,} contacts a month "
        "off people's queues",
        f"next review {NEXT_REVIEW}",
    ]
    return lines


def main():
    print("\n".join(show(memo())))


if __name__ == "__main__":
    main()
