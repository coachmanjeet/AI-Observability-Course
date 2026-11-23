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
"""
import math
from decimal import Decimal as D

import yaml

from maturity.funding import HERE as FUNDING_DIR
from metering.traffic import month
from metering.value import (HUMAN_PER_CONTACT, START,
                            by_conversation, outcomes, tree)

SAMPLE = D("0.05")        # sampled review share (policy/tiers)
CASH_SAVED = D("0")       # no staffing change agreed yet
GUARDRAIL = "resolved in 7 days >= 89%; holdout within 2 pts"
NEXT_REVIEW = "Jul 19, 2027"


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
    return {
        "first": t["first"], "resolved": t["resolved"],
        "spend": spend, "total": total, "agents": agents,
        "released": released,
        "released_usd": HUMAN_PER_CONTACT * released,
        "break_even": math.ceil(total / HUMAN_PER_CONTACT),
    }


def show(m):
    pct = 100 * m["resolved"] / m["first"]
    lines = [
        "Funding memo: Speedy, Pronto tenant, Q2 2027",
        f"cohort      {m['first']:,} first contacts, Feb 2027;",
        "            May holdout: 10% to people, same mix",
        f"baseline    resolved in 7 days {pct:.1f}%",
        f"guardrail   {GUARDRAIL}",
        "spend a month, USD",
    ]
    for k, v in m["spend"].items():
        lines.append(f"  {k:<24}{v:>11,.2f}")
    lines.append(f"  {'total':<24}{m['total']:>11,.2f}")
    lines += [
        f"capacity    {m['released']:,} contacts, "
        f"${m['released_usd']:,.2f} of people's time",
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
