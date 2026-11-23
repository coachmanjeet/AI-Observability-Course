"""The AI control tower's weekly view of the fleet (Chapter 18).

Usage: python -m orchestration.tower [OUT_DIR]

Reads one week of receipt summaries for every agent, first and
third party, and shows what a control tower needs on one screen:
maturity, how many of the seven questions the receipts answer,
deny rate, cost per action and outcome rate. Then it lists the
gaps it routes to owners, and compares the estate with Nov 14.
"""
import json
import pathlib
import sys

from maturity.assess import assess

HERE = pathlib.Path(__file__).parent
# the questions each level guarantees; a receipt may answer
# more, which the tower doesn't credit
ANSWERS = {"R4": 7, "R3": 5, "R2": 3, "R1": 2}
MISSING = {"R3": "at what cost, where",
           "R1": "for whom, knowing what, rule, cost, where"}


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def row(a, level):
    t, n = a["tower"], a["actions_7d"]
    counts = {"R4": a["r4_receipts_7d"], "R3": t["R3"],
              "R1": t["R1"]}
    answered = sum(ANSWERS[k] * v for k, v in counts.items())
    share = 100 * answered / (7 * n)
    cost = (f"${float(t['cost']) / n:.3f}" if t["cost"]
            else "n/a")
    done = (f"{round(100 * t['achieved'])}%"
            if t["achieved"] is not None else "n/a")
    return {"agent": a["name"], "kind": a["kind"],
            "level": level, "actions": n,
            "answered": round(share),
            "answered_exact": round(share, 2),
            "r4_share": round(100 * counts["R4"] / n, 2),
            "deny_pct": round(100 * t["denies"] / n, 1),
            "cost_per_action": cost, "outcomes": done,
            "counts": counts}


def gaps(rows):
    out = []
    for r in rows:
        for lvl in ("R3", "R1"):
            if r["counts"][lvl]:
                n = r["counts"][lvl]
                share = round(100 * n / r["actions"])
                out.append((r["agent"], f"{share}% {lvl}: no "
                            f"{MISSING[lvl]}"))
    return out


def tower(fleet, before):
    result = assess(fleet)
    levels = {a["name"]: lvl for a, lvl, _ in result["rows"]}
    rows = [row(a, levels[a["name"]]) for a in fleet["agents"]]
    then = assess(before)
    return rows, result, then


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    fleet = load(HERE / "fleet-2027-03-29.json")
    before = load(HERE.parent / "maturity" / "fleet.json")
    rows, now, then = tower(fleet, before)
    print("Control tower, week to Mar 29, 2027")
    print(f"{'agent':<8}{'kind':<5}{'lvl':>3}{'actions':>8}"
          f"{'answers':>8}{'R4':>7}{'deny':>6}{'$/act':>8}"
          f"{'done':>6}")
    for r in rows:
        print(f"{r['agent']:<8}{r['kind']:<5}{r['level']:>3}"
              f"{r['actions']:>8,}{r['answered_exact']:>7.1f}%"
              f"{r['r4_share']:>6.1f}%"
              f"{r['deny_pct']:>5}%{r['cost_per_action']:>8}"
              f"{r['outcomes']:>6}")
    print("Gaps routed to owners")
    for agent, gap in gaps(rows):
        print(f"  {agent:<7} {gap}")
    gone = ", ".join(f"{r['name']} ({r['retired_on']})"
                     for r in fleet["retired"])
    print(f"Retired: {gone}")
    print(f"Estate: L{now['estate']}, set by "
          f"{', '.join(now['weakest'])}; on Nov 14: "
          f"L{then['estate']}, set by "
          f"{', '.join(then['weakest'])}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "tower.json").write_text(json.dumps(
            {"rows": rows, "gaps": gaps(rows),
             "estate": now["estate"]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
