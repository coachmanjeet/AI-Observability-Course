"""A pricing simulator on pilot traffic (Chapter 29).

Usage: python -m metering.pricing [OUT_DIR]

Runs February for Pronto's three pilot tenants, then prices the
same usage six ways: per seat, per action, per conversation,
per outcome, prepaid credits, and a platform fee plus a smaller
per-outcome price. For each it reports what each tenant pays,
Pronto's gross margin, the tenant's price per resolved
conversation, and how the bill moves in a bad month, when
timeouts rise and fewer conversations resolve. The price points
are Pronto's candidates, informed by the market in Table 29.1.
"""
import json
import math
import pathlib
import sys
from decimal import Decimal as D

from metering.traffic import day, month
from metering.value import by_conversation, outcomes

PILOTS = ["tenant:hilltop", "tenant:corner", "tenant:bayside"]
SEATS = {"tenant:hilltop": 6, "tenant:corner": 3,
         "tenant:bayside": 9}
OVERHEAD = D("0.010")   # platform cost per conversation


def usage(tenant, timeouts=0.015):
    spans, convs = month(tenant, day("2027-02-01"), 28,
                         timeouts=timeouts)
    per = by_conversation(spans)
    rows = outcomes(convs, per)
    return {"conversations": len(convs),
            "actions": sum(len(v["tools"])
                           for v in per.values()),
            "resolved": sum(r["status"] == "achieved"
                            for r in rows),
            "cost": sum((v["cost"] for v in per.values()), D(0))
            + OVERHEAD * len(convs),
            "seats": SEATS[tenant]}


def credits(u):
    """1 credit a conversation, 1 an action; packs of 1,000."""
    used = u["conversations"] + u["actions"]
    return D(math.ceil(used / 1000)) * D("70")


MODELS = {
    "per seat": lambda u: D("49") * u["seats"],
    "per action": lambda u: D("0.10") * u["actions"],
    "per conversation": lambda u: D("0.60")
    * u["conversations"],
    "per outcome": lambda u: D("0.40") * u["resolved"],
    "credits": credits,
    "base + outcome": lambda u: D("99") + D("0.25")
    * u["resolved"],
}


def simulate(bad_timeouts=0.08):
    good = {t: usage(t) for t in PILOTS}
    bad = {t: usage(t, bad_timeouts) for t in PILOTS}
    out = {}
    for name, price in MODELS.items():
        bills = {t: price(good[t]) for t in PILOTS}
        total = sum(bills.values())
        cost = sum(good[t]["cost"] for t in PILOTS)
        res = sum(good[t]["resolved"] for t in PILOTS)
        worse = sum(price(bad[t]) for t in PILOTS)
        out[name] = {
            "bills": bills, "total": total,
            "margin": (total - cost) / total,
            "per_resolved": total / res,
            "bad_month": (worse - total) / total}
    return good, bad, out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    good, bad, out = simulate()
    print("Pricing simulator, Feb 2027, three pilot tenants")
    print(f"{'usage':<16}{'hilltop':>10}{'corner':>10}"
          f"{'bayside':>10}")
    for k in ("conversations", "actions", "resolved", "seats"):
        print(f"{k:<16}" + "".join(f"{good[t][k]:>10,}"
                                   for t in PILOTS))
    print(f"{'bill':<16}{'hilltop':>10}{'corner':>10}"
          f"{'bayside':>10}{'margin':>7}{'$/res':>6}{'bad':>5}")
    for name, r in out.items():
        b = r["bills"]
        print(f"{name:<16}"
              + "".join(f"{'$' + format(b[t], ',.2f'):>10}"
                        for t in PILOTS)
              + f"{r['margin']:>7.0%}{r['per_resolved']:>6.2f}"
              + f"{r['bad_month']:>+5.0%}")
    print("margin: gross, on cost to serve; "
          "$/res: revenue per resolution")
    res = sum(g["resolved"] for g in good.values())
    worse = sum(b["resolved"] for b in bad.values())
    print(f"bad month: timeouts 8%, resolved {res:,} "
          f"-> {worse:,}")
    if argv:
        o = pathlib.Path(argv[0])
        o.mkdir(parents=True, exist_ok=True)
        (o / "billable.json").write_text(json.dumps(
            {"at_what_cost": {"billable": [
                {"meter": "resolved_conversation"}]}},
            indent=2) + "\n")
        (o / "simulation.json").write_text(json.dumps(
            {k: {"total": str(v["total"]),
                 "margin": float(v["margin"]),
                 "bad_month": float(v["bad_month"])}
             for k, v in out.items()}, indent=2) + "\n")


if __name__ == "__main__":
    main()
