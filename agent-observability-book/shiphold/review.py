"""Ship or Hold for the control plane (Chapter 26).

Usage: python -m shiphold.review [OUT_DIR]

Three parts. First, assemble the full receipt for Saturday's
$40 refund from the outputs the chapters' labs wrote, tag each
field with the chapter that produced it, seal it and sign it.
Second, run the launch review: fourteen gates, each a live
check against a chapter's lab. Third, turn every condition and
hold into a dated 90-day plan with an owner.

Run after the other labs (make all), so build/ is filled.
"""

import copy
import datetime
import json
import pathlib
import sys

from audit.keys import lab_key
from audit.store import sign, signature_ok
from receipts.tools import record_hash, seal
from receipts.validate import RECEIPT, unanswered

ROOT = pathlib.Path(__file__).parent.parent
BUILD = ROOT / "build"
TARGET = (
    ROOT / "receipts" / "examples" / "02-speedy-refund-40.json"
)
REVIEW = datetime.date(2028, 1, 10)
SNAPSHOT = "fleet-2028-01-07.json"
FRESH_DAYS = 7          # evidence older than this can't decide
BAR = 99.0              # R4 coverage, exact, to enforce
FLEET = ("Speedy", "Pick", "Route", "Coder", "Ledger", "Promo")


def exceptions(at=None):
    """Exceptions in force at the review, by gate and agent."""
    import yaml
    at = at or REVIEW
    rows = yaml.safe_load((ROOT / "shiphold" /
                           "exceptions.yaml").read_text())
    live = [e for e in rows
            if e["granted"] <= at < e["expires"]]
    return rows, {(e["gate"], e.get("agent")): e for e in live}

# chapter, lab output, where the fragment goes
OVERLAYS = [
    (9, "packs/context-pack-1.4.0.json", "knowing_what"),
    (9, "memory/memory-reads.json", "knowing_what"),
    (11, "registry/who-speedy.json", None),
    (12, "identity/who-workload.json", None),
    (12, "delegation/for-whom.json", None),
    (13, "privilege/for-whom-scopes.json", None),
    (14, "policy/under-which-rule.json", None),
    (16, "oversight/rule-40.json", None),
    (17, "orchestration/via.json", None),
    (21, "value/receipt-outcome.json", None),
    (23, "entitlements/billing-account.json", None),
    (25, "residency/where-pronto.json", None),
]

# where each field was introduced, for fields no lab rewrites
TAGS = {
    "receipt_version": 2,
    "receipt_id": 2,
    "issued_at": 2,
    "conformance": 2,
    "consequence": 2,
    "who": 4,
    "who.kind": 3,
    "for_whom": 12,
    "knowing_what.model": 5,
    "knowing_what.sources": 8,
    "under_which_rule": 14,
    "did_what.action": 4,
    "did_what.action.via": 4,
    "did_what.action.mcp_method": 4,
    "did_what.effect": 4,
    "did_what.outcome": 21,
    "at_what_cost.tokens": 6,
    "at_what_cost.model_cost": 6,
    "at_what_cost.billable": 22,
    "at_what_cost.billing_account": 23,
    "where": 25,
    "evidence": 4,
    "evidence.mcp_session_id": 4,
    "evidence.conversation_id": 17,
    "integrity": 7,
}

QUESTIONS = [
    "who",
    "for_whom",
    "knowing_what",
    "under_which_rule",
    "did_what",
    "at_what_cost",
    "where",
]


def leaves(obj, path=""):
    """Every scalar or list path in a receipt."""
    if isinstance(obj, dict) and obj:
        for k, v in obj.items():
            yield from leaves(v, f"{path}.{k}" if path else k)
    else:
        yield path, obj


def tag_for(path):
    parts = path.split(".")
    for n in range(len(parts), 0, -1):
        key = ".".join(parts[:n])
        if key in TAGS:
            return TAGS[key]
    return 2


def merge(base, frag, chapter, tags, path=""):
    for k, v in frag.items():
        p = f"{path}.{k}" if path else k
        if isinstance(v, dict) and isinstance(
            base.get(k), dict
        ):
            merge(base[k], v, chapter, tags, p)
        else:
            base[k] = copy.deepcopy(v)
            for leaf, _ in leaves(v, p):
                tags[leaf] = chapter


def assemble():
    """The $40 refund's receipt, from every chapter's output."""
    target = json.loads(TARGET.read_text())
    rec = copy.deepcopy(target)
    tags = {p: tag_for(p) for p, _ in leaves(rec)}
    for chapter, name, under in OVERLAYS:
        frag = json.loads((BUILD / name).read_text())
        if under:
            frag = {under: frag}
        merge(rec, frag, chapter, tags)
    prev = target["integrity"]["prev_hash"]
    rec = seal(rec, prev)
    rec["integrity"]["signature"] = sign(
        lab_key(), rec["integrity"]["hash"]
    )
    for p in ("integrity.hash", "integrity.signature"):
        tags[p] = 7
    real = sorted(
        p
        for p, v in leaves(rec)
        if p in dict(leaves(target))
        and dict(leaves(target))[p] != v
        and not p.startswith("integrity")
    )
    return rec, tags, real


def short(v, width=22):
    if isinstance(v, dict):
        v = " ".join(
            short(x, 99)
            for x in v.values()
            if not isinstance(x, (dict, list))
        )
    elif isinstance(v, list):
        v = (
            ", ".join(
                (
                    short(next(iter(x.values())), 99)
                    if isinstance(x, dict)
                    else str(x)
                )
                for x in v
            )
            or "none"
        )
    v = str(v)
    return v if len(v) <= width else v[: width - 1] + "…"


LABELS = {
    "for_whom": "for whom",
    "knowing_what": "knowing",
    "under_which_rule": "rule",
    "did_what": "did",
    "at_what_cost": "cost",
}


def show_receipt(rec, tags):
    print(f"{'answer':<12}{'field':<16}{'value':<23}ch")
    for section, body in rec.items():
        if not isinstance(body, dict):
            print(
                f"{short(section, 27):<28}{short(body):<23}"
                f"{tags[section]}"
            )
            continue
        label = LABELS.get(section, section)
        for k, v in body.items():
            p = f"{section}.{k}"
            chs = sorted(
                {
                    c
                    for leaf, c in tags.items()
                    if leaf == p or leaf.startswith(p + ".")
                }
            )
            print(
                f"{label:<12}{short(k, 15):<16}"
                f"{short(v):<23}"
                f"{','.join(map(str, chs))}"
            )
            label = ""


# ---- the launch review --------------------------------------


def gates(rec):
    """Fourteen gates: (name, chapter, status, detail)."""
    # imported here so the receipt prints even if a lab moved
    from comply import evidence, govcloud, residency
    from orchestration import tower as tw
    from policy import gateway, oversight, redteam

    out = []
    errors = list(RECEIPT.iter_errors(rec))
    missing = unanswered(rec)
    out.append(
        (
            "full receipt valid",
            26,
            "pass" if not errors and not missing else "hold",
            f"{7 - len(missing)} of 7 answered",
        )
    )
    ok = record_hash(rec) == rec["integrity"][
        "hash"
    ] and signature_ok(
        lab_key().public_key(),
        rec["integrity"]["signature"],
        rec["integrity"]["hash"],
    )
    out.append(
        (
            "hash and signature",
            7,
            "pass" if ok else "hold",
            "verified",
        )
    )
    fleet = tw.load(tw.HERE / SNAPSHOT)
    as_of = datetime.date.fromisoformat(fleet["as_of"])
    age = (REVIEW - as_of).days
    out.append(
        (
            "fleet snapshot",
            18,
            "pass" if age <= FRESH_DAYS else "hold",
            f"week to {as_of:%b %d}, {age} days old",
        )
    )
    agents = fleet["agents"]
    owned = all(a["registered"] and a["owner"] for a in agents)
    gone = len(fleet["retired"])
    out.append(
        (
            "registered, owned",
            11,
            "pass" if owned else "hold",
            f"{len(agents)} agents, {gone} retired",
        )
    )
    own_id = all(a["identity"] == "own" for a in agents)
    out.append(
        (
            "own identity",
            12,
            "pass" if own_id else "hold",
            "all agents",
        )
    )
    passed, total = gateway.run_cases()
    out.append(
        (
            "policy tests",
            14,
            "pass" if passed == total else "hold",
            f"{passed} of {total}",
        )
    )
    from policy.boundary import run as only_path
    path = {label: outcome for label, outcome, _ in only_path()}
    alone = path["direct, Speedy's own token"] == "reject" and \
        path["engine down, refund $40"] == "deny"
    out.append(
        (
            "only path",
            14,
            "pass" if alone else "hold",
            "direct calls rejected",
        )
    )
    rows, _ = redteam.attacks()
    blocked = sum(r[2] for r in rows)
    fine = all(redteam.normal())
    persuaded = (
        oversight.approve(
            "ord_5640",
            "60.00",
            {
                "amount": "60.00",
                "photo": True,
                "refunds_30d": 0,
            },
            "user:lead",
        )[0]
        is None
    )
    closed = blocked + persuaded
    out.append(
        (
            "red team",
            15,
            "pass" if closed == len(rows) and fine else "hold",
            f"{closed} of {len(rows)} closed",
        )
    )
    tier = oversight.tier_for("85.00")["tier"]
    out.append(
        (
            "$85 needs approval",
            16,
            "pass" if tier == "act_with_approval" else "hold",
            tier,
        )
    )
    retired = json.loads(
        (BUILD / "fleetops" / "retired.json").read_text()
    )
    out.append(
        (
            "retired versions",
            19,
            "pass" if retired["receipts_kept"] else "hold",
            f"{retired['receipts_kept']} receipts resolve",
        )
    )
    rows, _, _ = tw.tower(
        fleet, tw.load(ROOT / "maturity" / "fleet.json")
    )
    _, live = exceptions()
    short = [r for r in rows if r["r4_share"] < BAR]
    held = [r["agent"] for r in short
            if ("R4 coverage", r["agent"]) not in live]
    covered = [live[("R4 coverage", r["agent"])]["id"]
               for r in short if r["agent"] not in held]
    detail = ", ".join(held) + " 0%" if held else "all agents"
    if covered:
        detail += "; Pick " + ", ".join(covered)
    out.append(
        (
            "R4 coverage",
            18,
            "hold" if held else "pass",
            detail,
        )
    )
    pack = evidence.pack()
    gaps = [r["id"] for r in pack if r["status"] == "gap"]
    ex = live.get(("evidence pack", None))
    status = ("pass" if not gaps
              else "excepted" if ex else "hold")
    out.append(
        (
            "evidence pack",
            24,
            status,
            (f"{', '.join(gaps)}, {ex['id']} to "
             f"{ex['expires']:%b %d}") if ex else
            (f"gap: {', '.join(gaps)}" if gaps else "met"),
        )
    )
    model = residency.pick_model(
        "tenant:fresca", ("eu-west-1",)
    )
    out.append(
        (
            "residency failover",
            25,
            (
                "pass"
                if residency.REGIONS[model] == "EU"
                else "hold"
            ),
            model,
        )
    )
    prof = govcloud.load("gov-profile.yaml")
    dep = govcloud.fixed(govcloud.load("gov-deploy.yaml"))
    bad = [c for c, p, _ in govcloud.review(dep, prof) if p]
    m = govcloud.monitor(prof)
    auto = m["automated"] / m["checks"]
    retire = prof["models"]["model-a"]["retires"]
    days = (retire - REVIEW).days
    status = (
        "hold"
        if bad or auto < 0.8
        else "condition" if days < 90 else "pass"
    )
    out.append(
        (
            "gov boundary",
            25,
            status,
            f"model-a retires in {days}d",
        )
    )
    out = out[:1] + sorted(out[1:], key=lambda g: g[1])
    return out, held


PLAN = {
    "R4 coverage": [
        (
            28,
            "Pick: batch path through the gateway",
            "team:fulfillment",
        ),
        (
            30,
            "Ledger: R4 receipts from server spans",
            "team:finance",
        ),
        (
            60,
            "Promo: partner traces in contract",
            "team:marketing",
        ),
    ],
    "evidence pack": [
        (45, "ISO A.5.2 impact assessment", "team:governance")
    ],
    "gov boundary": [
        (
            45,
            "Gov: model-b, rerun evals inside",
            "team:platform",
        )
    ],
}
ALWAYS = [
    (0, "enforce mode: 10% canary", "team:platform"),
    (14, "enforce mode: all shipped agents", "team:platform"),
    (30, "first monthly evidence pack", "team:governance"),
    (74, "Receipt v0.2: decide candidates", "team:governance"),
    (90, "re-review: Ship or Hold", "team:governance"),
]


def plan(results):
    items = list(ALWAYS)
    for name, _, status, _ in results:
        if status != "pass":
            items += PLAN.get(name, [])
    return sorted(items)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rec, tags, real = assemble()
    print("The full receipt: Saturday's $40 refund")
    show_receipt(rec, tags)
    print(
        f"real values replacing Chapter 2 targets: {len(real)}"
    )
    for p in real:
        print(f"  {p}")
    results, held = gates(rec)
    print()
    print("Ship or Hold: Pronto control plane, Jan 10, 2028")
    print(f"{'gate':<22}{'ch':>3}  {'result':<10}detail")
    for name, ch, status, detail in results:
        print(f"{name:<22}{ch:>3}  {status:<10}{detail}")
    shipped = [a for a in FLEET if a not in held]
    blocking = [
        r
        for r in results
        if r[2] == "hold" and r[0] != "R4 coverage"
    ]
    verdict = "HOLD" if blocking else "SHIP"
    print(
        f"verdict: {verdict} enforce for "
        f"{', '.join(shipped)}"
    )
    if held:
        print(f"         HOLD {', '.join(held)} (observe only)")
    rows, live = exceptions()
    print("Exceptions: scope, end date, accepted by")
    for e in rows:
        if e in live.values():
            print(f"  {e['id']}  {e['scope']:<37}"
                  f"to {e['expires']:%b %d}  "
                  f"{e['accepted_by']}")
    for e in rows:
        if e not in live.values():
            print(f"  {e['id']}  granted {e['granted']:%b %d}, "
                  f"lapsed {e['expires']:%b %d}; renewed "
                  f"{REVIEW:%b %d}")
    print("90-day plan:")
    for day, what, owner in plan(results):
        due = REVIEW + datetime.timedelta(days=day)
        print(f"  {due:%b %d}  {what:<38}{owner[5:]}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "full-receipt.json").write_text(
            json.dumps(rec, indent=2) + "\n"
        )
        (out / "tags.json").write_text(
            json.dumps(tags, indent=2) + "\n"
        )
        seal = {"integrity": rec["integrity"]}
        (out / "integrity.json").write_text(
            json.dumps(seal, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
