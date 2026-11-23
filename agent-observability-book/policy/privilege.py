"""Least privilege for agents (Chapter 18).

Usage: python -m policy.privilege [OUT_DIR]

Compares three things for each agent: what its credentials allow
(grants), what it used in the last 30 days (from receipts), and
what its tasks need. Used means the gateway checked the scope to
allow a call, not that the call's token carried it. The
difference is the permission diff:
unused grants to remove, risky ones first, drift since the last
review, and a token per task sized to that task alone.
"""
import json
import pathlib
import sys

import yaml

HERE = pathlib.Path(__file__).parent
WINDOW = "30 days to Feb 21, 2027"
PREV, NOW = "2027-01-22", "2027-02-22"

# grants that can do damage nobody can undo quickly
RISKY = {
    "refunds:create:any": "moves money, any amount",
    "customers:write:any": "changes any customer",
    "repo:admin:platform": "can change branch rules",
    "ci:secrets:read": "reads release credentials",
    "warehouse:admin": "reconfigures the warehouse",
    "pricing:write": "changes live prices",
}


def load(name):
    return yaml.safe_load((HERE / name).read_text())


def covers(broad, narrow):
    """True if scope `broad` includes scope `narrow`."""
    if broad == narrow:
        return True
    b, _, bq = broad.rpartition(":")
    n, _, nq = narrow.rpartition(":")
    if b != n:
        return False
    if bq == "any":
        return True
    if bq.startswith("max_") and nq.startswith("max_"):
        return int(bq[4:]) >= int(nq[4:])
    return False


def task_scopes(agent, task):
    """The scopes one task needs: the token asks for these."""
    return sorted(load("tasks.yaml")[agent][task])


def review():
    grants = load(f"grants/{NOW}.yaml")
    before = load(f"grants/{PREV}.yaml")
    usage = load("usage-30d.yaml")
    tasks = load("tasks.yaml")
    out = {}
    for agent, granted in grants.items():
        used = {s for s, n in usage.get(agent, {}).items() if n}
        needed = {s for t in tasks.get(agent, {}).values()
                  for s in t}
        keep = used | needed
        unused = sorted(set(granted) - used)
        out[agent] = {
            "granted": sorted(granted), "used": sorted(used),
            "unused": unused,
            "risky_unused": [s for s in unused if s in RISKY],
            "drift": sorted(set(granted) - set(before[agent])),
            "keep": sorted(keep & set(granted)),
            "add": sorted(keep - set(granted)),
            "remove": sorted(set(granted) - keep)}
    return out


def show(rep):
    lines = [f"Least privilege, {WINDOW}",
             "agent    granted  used  unused  risky"]
    tot = [0, 0, 0, 0]
    for a, r in rep.items():
        row = [len(r["granted"]), len(r["used"]),
               len(r["unused"]), len(r["risky_unused"])]
        tot = [x + y for x, y in zip(tot, row)]
        lines.append(f"{a:<8}{row[0]:>8}{row[1]:>6}"
                     f"{row[2]:>8}{row[3]:>7}")
    pct = round(100 * tot[1] / tot[0])
    lines.append(f"{'fleet':<8}{tot[0]:>8}{tot[1]:>6}"
                 f"{tot[2]:>8}{tot[3]:>7}  ({pct}% used)")
    lines.append("Risky and unused")
    for a, r in rep.items():
        for s in r["risky_unused"]:
            lines.append(f"  {a:<7} {s:<21} {RISKY[s]}")
    lines.append("Drift since the Jan 22 review")
    for a, r in rep.items():
        for s in r["drift"]:
            lines.append(f"  {a:<7} + {s}")
    lines.append("Carried in tokens versus used by calls")
    for a, scopes in load("carried-30d.yaml").items():
        for s, n in scopes.items():
            c, u = n["carried"], n["used"]
            lines.append(f"  {a:<7} {s:<22} carried "
                         f"{c:>3}  used {u:>3}")
    sp = rep["speedy"]
    lines.append("Speedy, proposed grants")
    lines.append("  keep    " + ", ".join(sp["keep"]))
    lines.append("  add     " + ", ".join(sp["add"]))
    risky = sum(s in RISKY for s in sp["remove"])
    lines.append(f"  remove  {len(sp['remove'])} grants, "
                 f"{risky} of them risky")
    lines.append("Speedy, token per task")
    for t in load("tasks.yaml")["speedy"]:
        lines.append(f"  {t:<15} "
                     + " ".join(task_scopes("speedy", t)))
    return lines


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rep = review()
    print("\n".join(show(rep)))
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(
            json.dumps(rep, indent=2) + "\n")
        scopes = task_scopes("speedy", "refund_damaged")
        (out / "for-whom-scopes.json").write_text(json.dumps(
            {"for_whom": {"scopes": scopes}}, indent=2) + "\n")


if __name__ == "__main__":
    main()
