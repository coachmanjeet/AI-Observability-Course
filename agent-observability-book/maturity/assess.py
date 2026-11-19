"""Scores an agent estate on the five-level maturity model.

Usage: python -m maturity.assess FLEET.json [--fail-below LEVEL]

Used in Chapter 3. Each agent climbs the ladder until it fails a check.
The first failed check is its next step. The estate is only as mature
as its weakest agent, because that agent is where the next incident
starts. Copy fleet.json, describe your own agents, and run it.
"""
import argparse
import json
import pathlib
import sys
import textwrap

NAMES = {1: "Invisible", 2: "Inventoried", 3: "Identified",
         4: "Bounded and traced", 5: "Accountable"}
WHERE_RULES = {"in_prompt": "in the prompt", "none": "nowhere"}


def has_owner(a):
    return a["owner"] not in (None, "", "unknown")


def all_receipted(a):
    n = a["actions_7d"]
    return n > 0 and a["r4_receipts_7d"] == n


# Each rung lists the checks an agent must pass to stand on it,
# and the next step to print when a check fails.
LADDER = [
    (2, [(lambda a: a["registered"],
          "register it and name an owner, or shut it off"
          " (Ch 14, 15)"),
         (has_owner,
          "name an owner team that answers for it (Ch 15)")]),
    (3, [(lambda a: a["identity"] == "own",
          "give it its own identity; it runs on a {identity}"
          " credential (Ch 16)"),
         (lambda a: a["access"] == "scoped",
          "scope its access to what its job needs (Ch 18)")]),
    (4, [(lambda a: a["policy"] == "outside_model",
          "enforce its rules outside the model; today they"
          " live {rules} (Ch 19)"),
         (lambda a: a["traced"],
          "trace every action, end to end (Ch 4, 5)")]),
    (5, [(all_receipted,
          "emit an R4 receipt for every consequential action;"
          " {r4_receipts_7d:,} of {actions_7d:,} have one"
          " (Ch 2)")]),
]

# The same checks, cut by pillar instead of by rung.
PILLARS = {
    "Discover": lambda a: (a["registered"] and has_owner(a)
                       and a["identity"] == "own"),
    "Govern": lambda a: (a["access"] == "scoped"
                        and a["policy"] == "outside_model"),
    "Observe": lambda a: a["traced"] and all_receipted(a),
}


def score(agent):
    """Return (level, next step) for one agent."""
    for level, checks in LADDER:
        for passes, step in checks:
            if not passes(agent):
                where = WHERE_RULES.get(agent["policy"], "")
                next_step = step.format(rules=where, **agent)
                return level - 1, next_step
    return 5, "keep it there; review receipts at launch (Ch 34)"


def assess(fleet):
    rows = [(a, *score(a)) for a in fleet["agents"]]
    estate = min(level for _, level, _ in rows)
    weakest = [a["name"] for a, lvl, _ in rows if lvl == estate]
    pillars = {p: sum(test(a) for a in fleet["agents"])
               for p, test in PILLARS.items()}
    return {"rows": rows, "estate": estate, "weakest": weakest,
            "pillars": pillars, "total": len(rows)}


def wrap(text):
    """Wrap at 64 columns, keeping "(Ch 14, 15)" in one piece."""
    head, _, ref = text.rpartition(" (")
    if ref:
        text = head + " (" + ref.replace(" ", "\u00a0")
    out = textwrap.fill(text, width=64, initial_indent="   ",
                        subsequent_indent="         ")
    return out.replace("\u00a0", " ")


def report(fleet, result):
    lines = [f"{fleet['estate']} estate, {fleet['as_of']}, "
             f"{result['total']} agents", ""]
    for agent, level, step in result["rows"]:
        lines.append(f"L{level} {agent['name']:<10} {agent['kind']:<8}"
                     f"{NAMES[level]}")
        lines.append(wrap("next: " + step))
    lines += ["", f"Estate level: L{result['estate']} "
              f"{NAMES[result['estate']]}, set by "
              f"{', '.join(result['weakest'])}",
              "Pillars complete: " + ", ".join(
                  f"{p} {n}/{result['total']}"
                  for p, n in result["pillars"].items())]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("fleet", type=pathlib.Path)
    parser.add_argument("--fail-below", type=int, default=0,
                        help="exit 1 if the estate is below this level")
    args = parser.parse_args(argv)
    fleet = json.loads(args.fleet.read_text(encoding="utf-8"))
    result = assess(fleet)
    print(report(fleet, result))
    return 1 if result["estate"] < args.fail_below else 0


if __name__ == "__main__":
    sys.exit(main())
