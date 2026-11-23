"""Provisioning, entitlements and FinOps (Chapter 23).

Usage: python -m metering.entitlements [OUT_DIR]

Each tenant's plan says which agents it may run, which model
tier, how many conversations a month, and a monthly cap on what
it can be billed. The runtime checks the plan before every
conversation. Pronto also keeps a daily cost budget per tenant,
because under outcome pricing a runaway loop costs Pronto, not
the tenant: thresholds alert at 50% and 80%, and at 100% a
budget kill switch pauses new conversations for that tenant
only.

The monthly cap is applied when an invoice is rated, against that
invoice: a charge that would cross it is cut to the headroom and
the rest is waived on the line, never carried forward. A late
outcome is billed on the invoice where it lands, against that
month's cap, and a later credit returns only what was charged.
"""
import json
import pathlib
import sys
from decimal import Decimal as D

PLANS = {
    "starter": {"agents": {"speedy"}, "models": {"small"},
                "quota": 600, "cap": D("250")},
    "standard": {"agents": {"speedy"},
                 "models": {"small", "standard"},
                 "quota": 2000, "cap": D("600")},
    "plus": {"agents": {"speedy", "route"},
             "models": {"small", "standard"},
             "quota": 4000, "cap": D("1200")},
}
TENANTS = {"tenant:hilltop": "standard",
           "tenant:corner": "starter",
           "tenant:bayside": "plus"}
COST = D("0.015")                 # model cost per conversation
DAILY_BUDGET = {"tenant:hilltop": D("6"),
                "tenant:corner": D("3"),
                "tenant:bayside": D("10")}
ALERTS = (D("0.5"), D("0.8"))


class Runtime:
    def __init__(self):
        self.used = {t: 0 for t in TENANTS}
        self.spend = {t: D(0) for t in TENANTS}
        self.paused, self.log = set(), []

    def start(self, tenant, agent="speedy", model="standard",
              at=""):
        """Check the plan, then the budget, then run."""
        plan = PLANS[TENANTS[tenant]]
        if agent not in plan["agents"]:
            return "denied: agent not in plan"
        if model not in plan["models"]:
            return "denied: model tier not in plan"
        if self.used[tenant] >= plan["quota"]:
            return "denied: monthly quota reached"
        budget = DAILY_BUDGET[tenant]
        if tenant not in self.paused and \
                self.spend[tenant] + COST > budget:
            self.paused.add(tenant)
            self.log.append((at, "kill switch: new "
                                 "conversations paused"))
        if tenant in self.paused:
            return "denied: budget kill switch"
        self.used[tenant] += 1
        before = self.spend[tenant] / DAILY_BUDGET[tenant]
        self.spend[tenant] += COST
        after = self.spend[tenant] / DAILY_BUDGET[tenant]
        for level in ALERTS:
            if before < level <= after:
                self.log.append(
                    (at, f"alert {level:.0%} of daily budget"))
        return "ok"


def runaway():
    """Bayside's webhook retries open a conversation every
    second for 20 minutes, from 14:00, on top of normal work."""
    rt = Runtime()
    rt.used["tenant:bayside"] = 1490   # month to date, May 10
    rt.spend["tenant:bayside"] = D("4.20")   # today, normal
    results = []
    for sec in range(20 * 60):
        at = f"14:{sec // 60:02d}"
        results.append(rt.start("tenant:bayside", at=at))
    other = rt.start("tenant:hilltop", at="14:20")
    return rt, results, other


PER_OUTCOME = D("0.25")          # base plus outcome, from July


def cap_charge(billed, amount, cap):
    """(charged, waived) for one charge on an invoice that has
    already billed `billed` against `cap`."""
    room = max(cap - billed, D("0"))
    charged = min(amount, room)
    return charged, amount - charged


def cap_example():
    cap = PLANS[TENANTS["tenant:corner"]]["cap"]
    july = cap_charge(D("249.90"), PER_OUTCOME, cap)
    august = cap_charge(D("112.25"), PER_OUTCOME, cap)
    return cap, july, august


def billing_account(tenant):
    return {"at_what_cost": {"billing_account": tenant}}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    print("Plans, May 10, 2027")
    for t, p in TENANTS.items():
        plan = PLANS[p]
        agents = ",".join(sorted(plan["agents"]))
        print(f"  {t[7:]:<8}{p:<9}{agents:<13}"
              f"{plan['quota']:>6,}/mo  cap ${plan['cap']:,}")
    rt = Runtime()
    rt.used["tenant:hilltop"] = 2000
    print("Checks")
    for label, args in [
            ("corner runs route", ("tenant:corner", "route")),
            ("corner, standard model",
             ("tenant:corner", "speedy", "standard")),
            ("hilltop, conversation 2,001",
             ("tenant:hilltop",))]:
        print(f"  {label:<29}{rt.start(*args)}")
    rt, results, other = runaway()
    ok = results.count("ok")
    print("Runaway: Bayside webhook loop from 14:00")
    for at, what in rt.log:
        print(f"  {at}  {what}")
    print(f"  ran {ok:,} of {len(results):,}; spend today "
          f"${rt.spend['tenant:bayside']:.2f} of $10.00")
    print(f"  hilltop at 14:20: {other}")
    left = PLANS["plus"]["quota"] - 1490
    print(f"  without it: quota gone at 14:{left // 60:02d}, "
          "Bayside's customers")
    print("  shut out for the rest of May")
    cap, jul, aug = cap_example()
    print(f"Cap: corner, ${cap:.2f} an invoice, base fee included")
    print("  Jul 29  outcome $0.25, July invoice at $249.90")
    print(f"          charge ${jul[0]:.2f}, waive ${jul[1]:.2f} "
          "on the line")
    print("  Jul 30  conversation; resolves Aug 06, after close")
    print(f"          August invoice and cap: charge "
          f"${aug[0]:.2f}")
    print(f"  Aug 10  Jul 29 outcome reversed: credit "
          f"${jul[0]:.2f}, August")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "billing-account.json").write_text(json.dumps(
            billing_account("tenant:pronto"), indent=2) + "\n")


if __name__ == "__main__":
    main()
