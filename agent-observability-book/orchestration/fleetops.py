"""Fleet operations: canary, drift, incident drill, retirement.

Usage: python -m orchestration.fleetops [OUT_DIR]

Chapter 25. Speedy 2.4.0, approved after its security review,
takes 10% of conversations as a canary. The receipts of both
versions are compared every hour; a significant drift opens an
incident, and the runbook contains it, finds the cause in the
receipts, rolls back through the registry and retires the
version, without losing any record of what it did.
"""
import json
import math
import pathlib
import random
import sys

OLD, NEW = "2.3.1", "2.4.0"
# what each version does per conversation (seeded simulation)
RATES = {OLD: {"refund": 0.26, "over_50": 0.010},
         NEW: {"refund": 0.37, "over_50": 0.045}}


def conversations(seed=7, n=1200, canary=0.10):
    """One day of Speedy's conversations, as receipts."""
    rnd, out = random.Random(seed), []
    for i in range(n):
        v = NEW if rnd.random() < canary else OLD
        refund = rnd.random() < RATES[v]["refund"]
        over = refund and rnd.random() < RATES[v]["over_50"] / \
            RATES[v]["refund"]
        out.append({"receipt_id": f"rcpt_{seed}_{i:04d}",
                    "who": {"agent_version": v},
                    "refund": refund,
                    "decision": "deny" if over else "allow"})
    return out


def two_prop_p(k1, n1, k2, n2):
    """Two-sided p-value that two rates differ."""
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = abs(k1 / n1 - k2 / n2) / se
    return math.erfc(z / math.sqrt(2))


def compare(rows):
    by = {v: [r for r in rows if r["who"]["agent_version"] == v]
          for v in (OLD, NEW)}
    out = {}
    for metric, key, val in [("refund rate", "refund", True),
                             ("deny rate", "decision", "deny")]:
        a, b = by[OLD], by[NEW]
        ka = sum(r[key] == val for r in a)
        kb = sum(r[key] == val for r in b)
        out[metric] = {"old": ka / len(a), "new": kb / len(b),
                       "p": two_prop_p(ka, len(a), kb, len(b))}
    return by, out


REGISTRY = {f"agent://pronto/speedy@{OLD}": "approved",
            f"agent://pronto/speedy@{NEW}": "canary"}
TRAFFIC = {OLD: 0.90, NEW: 0.10}


def drill(rows, by, drift):
    """The runbook, step by step, in minutes from the alert."""
    log = [(0, f"alert: {NEW} refund rate "
               f"{drift['refund rate']['new']:.0%} vs "
               f"{drift['refund rate']['old']:.0%}")]
    TRAFFIC.update({OLD: 0.90, NEW: 0.10})
    log.append((2, f"contain: {NEW} moved to approval tier"))
    suspect = [r for r in by[NEW] if r["refund"]]
    log.append((9, f"investigate: {len(suspect)} {NEW} refund "
                   "receipts"))
    TRAFFIC.update({OLD: 1.0, NEW: 0.0})
    REGISTRY[f"agent://pronto/speedy@{NEW}"] = "rolled_back"
    log.append((13, f"recover: canary to 0%, {OLD} at 100%"))
    log.append((14, f"verify: next receipts are {OLD}"))
    return log


def retire(version, receipts):
    """Retire a version: no new identities, records kept."""
    REGISTRY[f"agent://pronto/speedy@{version}"] = "retired"
    kept = [r for r in receipts
            if r["who"]["agent_version"] == version]
    return {"registry_ref":
            f"registry://pronto/agents/speedy@{version}",
            "state": "retired", "receipts_kept": len(kept)}


MIN_N, ALPHA = 200, 0.01


def watch(days=3):
    """Compare versions daily; alert on enough evidence."""
    rows, table = [], []
    for day in range(1, days + 1):
        rows += conversations(seed=day)
        by, drift = compare(rows)
        n = len(by[NEW])
        ready = n >= MIN_N
        alert = ready and any(d["p"] < ALPHA
                              for d in drift.values())
        table.append((day, n, drift, ready, alert))
        if alert:
            return rows, by, drift, table
    return rows, by, drift, table


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows, by, drift, table = watch()
    print(f"Speedy canary from Apr 5, 2027: {NEW} on 10%")
    print("day  canary n  refunds old/new  denies old/new")
    for day, n, d, ready, alert in table:
        r, x = d["refund rate"], d["deny rate"]
        note = ("ALERT" if alert else
                "wait" if not ready else "ok")
        print(f"{day:>3}{n:>10}  {r['old']:>6.1%} "
              f"{r['new']:>6.1%}   {x['old']:>5.1%} "
              f"{x['new']:>5.1%}  {note}")
    print("Runbook drill")
    for minute, step in drill(rows, by, drift):
        print(f"  +{minute:>2} min  {step}")
    ret = retire(NEW, rows)
    print(f"Retire {NEW}: {ret['state']}, "
          f"{ret['receipts_kept']} receipts still resolve")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        sample = next(r for r in by[NEW] if r["refund"])
        (out / "canary-who.json").write_text(json.dumps(
            {"who": sample["who"]}, indent=2) + "\n")
        (out / "retired.json").write_text(
            json.dumps(ret, indent=2) + "\n")


if __name__ == "__main__":
    main()
