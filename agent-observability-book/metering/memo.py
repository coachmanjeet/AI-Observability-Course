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
from collections import Counter
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
# The last June decline finishes its 30 days on Jul 30, so the
# full May-June cohort can't be judged before then.
INTERIM, GATE = "Jul 19, 2027", "Aug 2, 2027"
UNPRICED = "tool and API calls, telemetry storage"


def arm(rows):
    """One arm's counts, the same way for Speedy and for people:
    pending cases are left out and listed; unknowns stay in, as
    not confirmed."""
    c = Counter(r["customer"] for r in rows)
    mature = len(rows) - c["pending"]
    return {"contacts": len(rows), "confirmed": c["resolved"],
            "mature": mature, "pending": c["pending"],
            "unknown": c["unknown"],
            "rate": c["resolved"] / mature if mature else None}


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
    rows = outcomes(convs, per)
    t = tree(convs, per, rows)
    speedy = arm(rows)
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
    rate = speedy["rate"]
    loaded = (total + t["people"]) / speedy["confirmed"]
    return {
        "first": t["first"], "resolved": t["resolved"],
        "customer": speedy["confirmed"], "rate": rate,
        "arm": speedy,
        "confirmed_cost": t["confirmed_cost"], "loaded": loaded,
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
    s = m["arm"]
    lines = [
        "Funding memo: Speedy, Pronto tenant, Q2 2027",
        f"cohort      {m['first']:,} first contacts, Feb 2027, "
        "as of Apr 19",
        "outcome     issue resolved within window, any handler",
        "            confirmed  mature  pending  unknown   rate",
        f"  Speedy    {s['confirmed']:>9,}{s['mature']:>8,}"
        f"{s['pending']:>9,}{s['unknown']:>9,}"
        f"{100 * s['rate']:>6.1f}%",
        "  people    not measured in February; the holdout, May on",
        f"autonomy    no person involved {auto:.1f}%, "
        "reported apart",
        f"holdout     {HOLDOUT:.0%} of first contacts to people, "
        "May and June",
        f"gate        {GATE}: Speedy minus people, 95% interval",
        "  counted   when mature: 7 days, declines 30, cases 7",
        "            after closing; pending left out of both arms",
        f"  {INTERIM[:6]}    interim counts per arm; no decision",
        f"  fund      low end at or above -{tol:.0f} pts",
        f"  stop      high end below -{tol:.0f} pts",
        "  otherwise insufficient evidence: hold scope, "
        "keep holdout",
        f"  width     at equal rates: 10% for a month "
        f"+/-{a:.1f} pts;",
        f"            {HOLDOUT:.0%} for {MONTHS} months +/-{b:.1f}",
        "spend a month, USD",
    ]
    for k, v in m["spend"].items():
        lines.append(f"  {k:<24}{v:>11,.2f}")
    lines.append(f"  {'total':<24}{m['total']:>11,.2f}")
    lines += [
        f"per confirmed resolution, {m['customer']:,}",
        f"  {'model + escalation':<24}"
        f"{m['confirmed_cost']:>11.3f}",
        f"  {'all priced lines':<24}{m['loaded']:>11.2f}",
        f"  not priced: {UNPRICED}",
        f"people      ${HUMAN_PER_CONTACT} a contact; per "
        "resolution: from the holdout",
        f"capacity    {m['released']:,} contacts, "
        f"${m['released_usd']:,.2f} of people's time",
        f"            less {m['holdout']:,} a month to the holdout",
        f"cash saved  ${CASH_SAVED:.2f} until staffing changes",
        f"break-even  {m['break_even']:,} contacts a month "
        "off people's queues",
        f"next review {GATE}",
    ]
    return lines


def main():
    print("\n".join(show(memo())))


if __name__ == "__main__":
    main()
