"""Build an evidence pack from receipts and controls (Ch 31).

Usage: python -m comply.evidence [OUT_DIR]

Each requirement in crosswalk.yaml names a check. Each check
looks at real artifacts built in earlier chapters (receipts and
their hash chain, deny records, autonomy tiers, the registry
snapshot, retention settings, the canary) and returns met,
partial or gap, with the evidence it used. The result is the
pack an auditor gets: one line per requirement, every line
traceable to a file or a lab.
"""
import json
import pathlib
import sys

import yaml

from receipts.tools import record_hash

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
EXAMPLES = ROOT / "receipts" / "examples"
MIN_DAYS = 183                   # "at least six months"


def load(name):
    return yaml.safe_load((HERE / name).read_text())


def receipts():
    recs = [json.loads((EXAMPLES / f).read_text())
            for f in ("01-speedy-order-lookup.json",
                      "02-speedy-refund-40.json")]
    ok = all(r["conformance"] == "R4" and
             record_hash(r) == r["integrity"]["hash"]
             for r in recs)
    return ("met" if ok else "gap"), "R4 receipts, hash chain"


def denies():
    from policy.redteam import attacks
    _, records = attacks()
    ok = all(r["under_which_rule"]["decision"] == "deny"
             for r in records)
    return ("met" if ok and records else "gap"), \
        f"{len(records)} deny records"


def risk_events():
    """Art 12(2): risk, post-market and deployer monitoring."""
    flagged, _ = denies()
    path = EXAMPLES / "03-outcome-refund-40.json"
    outcome = json.loads(path.read_text())
    watched, _ = monitoring()
    ok = flagged == watched == "met" and \
        outcome["record_type"] == "outcome"
    return ("met" if ok else "gap"), \
        "denies, outcomes, canary"


def oversight():
    from policy.oversight import respond, tier_for
    ok = tier_for("85.00")["tier"] == "act_with_approval" and \
        respond("pause").startswith("deny")
    return ("met" if ok else "gap"), "tiers, approvals, pause"


def retention():
    days = load("retention.yaml")
    ok = min(days["receipts"], days["approvals"]) >= MIN_DAYS
    return ("met" if ok else "gap"), \
        f"receipts kept {days['receipts']} days"


def disclosure():
    said = load("disclosure.yaml")
    ok = all("AI" in s or "automated" in s
             for s in said.values())
    return ("met" if ok else "gap"), "first line, every channel"


def impact():
    path = HERE / "impact" / "speedy.md"
    return ("met" if path.exists() else "gap"), \
        "no impact assessment on file"


def monitoring():
    from orchestration.fleetops import watch
    _, _, _, table = watch()
    return ("met" if table[-1][4] else "gap"), \
        "canary on receipts, tower"


def provenance():
    rec = json.loads((EXAMPLES / "02-speedy-refund-40.json")
                     .read_text())
    srcs = rec["knowing_what"]["sources"]
    ok = all(s.get("version") and s.get("authority")
             for s in srcs)
    return ("met" if ok else "gap"), \
        "sources: version, authority"


def third_party():
    from orchestration.tower import HERE as T, load as tl
    fleet = tl(T / "fleet-2027-03-29.json")
    weak = [a["name"] for a in fleet["agents"]
            if a["kind"] == "3P" and a["tower"]["R1"]]
    return ("partial" if weak else "met"), \
        f"{', '.join(weak)} at R1" if weak else "R3+"


def inventory():
    from orchestration.tower import HERE as T, load as tl
    fleet = tl(T / "fleet-2027-03-29.json")
    ok = all(a.get("owner") for a in fleet["agents"])
    return ("met" if ok else "gap"), \
        f"{len(fleet['agents'])} agents, owners"


def deactivate():
    from policy.oversight import respond
    ok = respond("revoke") == "no identity issued"
    return ("met" if ok else "gap"), "pause, revoke tested"


def access():
    from identity import delegation as dg
    from identity import workload as wl
    svid, _ = wl.attest(wl.SPEEDY, dg.AS)
    token, _ = dg.exchange(dg.login("cust_7f3a91"), svid,
                           dg.ASK)
    session = dg.login("cust_7f3a91")
    passthrough = dg.check(session, "orders:read:own")
    ok = token and passthrough == "wrong audience"
    return ("met" if ok else "gap"), \
        "own identity, 5-min tokens"


CHECKS = {f.__name__: f for f in
          (receipts, risk_events, oversight, retention,
           disclosure,
           impact, monitoring, provenance, third_party,
           inventory, deactivate, access)}


def pack():
    rows = []
    for req in load("crosswalk.yaml"):
        status, evidence = CHECKS[req["check"]]()
        rows.append({**req, "status": status,
                     "evidence": evidence})
    return rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows = pack()
    print(f"Evidence pack, Jun 7, 2027: "
          f"{len(rows)} requirements")
    last = None
    for r in rows:
        fw = r["fw"] if r["fw"] != last else ""
        last = r["fw"]
        print(f"{fw:<12}{r['id']:<14}{r['evidence']:<31}"
              f"{r['status']}")
    count = {s: sum(r["status"] == s for r in rows)
             for s in ("met", "partial", "gap")}
    print(f"met {count['met']}, partial {count['partial']}, "
          f"gap {count['gap']}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "evidence-pack.json").write_text(
            json.dumps(rows, indent=2) + "\n")
        rec = json.loads((EXAMPLES / "02-speedy-refund-40.json")
                         .read_text())
        canon = rec["integrity"]["canonicalization"]
        (out / "integrity.json").write_text(json.dumps(
            {"conformance": rec["conformance"],
             "integrity": {"canonicalization": canon}},
            indent=2) + "\n")


if __name__ == "__main__":
    main()
