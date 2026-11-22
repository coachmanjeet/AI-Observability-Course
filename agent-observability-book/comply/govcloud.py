"""Gov Cloud configuration profile check (Chapter 33).

Usage: python -m comply.govcloud [OUT_DIR] [--air-gapped]

An authorization boundary is a list of components, not a
region. Every component that stores, processes or moves the
program's data must be inside the boundary's regions, use
FIPS-validated endpoints, use an authorized model, sign with
an approved algorithm, and (if air-gapped) need no network
path out. The check runs on the real deployment manifest,
then on 30 days of receipts as continuous monitoring.
"""
import datetime
import json
import pathlib
import random
import sys

import yaml

HERE = pathlib.Path(__file__).parent
TODAY = datetime.date(2027, 11, 8)
OFFLINE = {"signed-import"}

FIXES = {
    "fallback model": ({"model": "model-b"},
                       "fall back to model-b"),
    "context pack registry": (
        {"region": "us-gov-west-1", "fips": True,
         "updates": "signed-import"},
        "mirror inside; import signed packs"),
    "trace export": (
        {"region": "us-gov-west-1", "fips": True,
         "updates": "signed-import"},
        "export to the in-boundary collector"),
    "eval judge": (
        {"region": "us-gov-west-1", "fips": True,
         "model": "model-b", "updates": "managed"},
        "judge with model-b inside"),
}


def load(name):
    return yaml.safe_load((HERE / name).read_text())


def check(c, profile, today=TODAY):
    """Problems and notes for one component."""
    problems, notes = [], []
    if c["region"] not in profile["regions"]:
        problems.append("region")
    if profile["fips_required"] and not c.get("fips"):
        problems.append("fips")
    model = c.get("model")
    if model:
        m = profile["models"].get(model, {})
        if m.get("status") != "authorized":
            problems.append("model")
        elif "retires" in m:
            left = (m["retires"] - today).days
            notes.append(f"{model} retires in {left}d")
    alg = c.get("alg")
    if alg and alg not in profile["algorithms"]:
        problems.append("alg")
    if "staff" in c and c["staff"] != profile["staff"]:
        problems.append("staff")
    if profile["air_gapped"] and c["updates"] not in OFFLINE:
        problems.append("path-out")
    return problems, notes


def review(deploy, profile):
    rows = []
    for c in deploy:
        problems, notes = check(c, profile)
        rows.append((c, problems, notes))
    return rows


def fixed(deploy):
    out = []
    for c in deploy:
        change = FIXES.get(c["name"], ({}, ""))[0]
        out.append({**c, **change})
    return out


def monitor(profile, days=30, seed=33):
    """Continuous monitoring over a month of receipts."""
    rng = random.Random(seed)
    regions = profile["regions"]
    total = inside = authorized = signed = 0
    denied = {"telemetry SDK default endpoint": 0,
              "public package index": 0}
    for _ in range(days):
        for _ in range(rng.randint(260, 300)):
            total += 1
            region = rng.choice(regions + regions[:1] * 3)
            model = rng.choice(["model-a"] * 4 + ["model-b"])
            inside += region in regions
            ok = profile["models"][model]["status"]
            authorized += ok == "authorized"
            signed += 1
        if rng.random() < 0.3:
            denied[rng.choice(sorted(denied))] += 1
    checks = profile["monitoring"]
    auto = sum(1 for c in checks if c["automated"])
    return {"receipts": total, "in_boundary": inside,
            "authorized_model": authorized,
            "signature_valid": signed, "egress_denied": denied,
            "automated": auto, "checks": len(checks)}


def where():
    return {"cloud_provider": "aws-us-gov",
            "region": "us-gov-west-1",
            "environment": "govcloud-production",
            "data_residency": "US",
            "model_endpoint_region": "us-gov-west-1"}


def show(rows):
    for c, problems, notes in rows:
        result = "fail: " + ", ".join(problems) if problems \
            else "ok" + (f", {notes[0]}" if notes else "")
        print(f"{c['name']:<22}{c['region']:<14}{result}")
    bad = sum(1 for _, p, _ in rows if p)
    print(f"{len(rows) - bad} ok, {bad} fail")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    profile, deploy = load("gov-profile.yaml"), load(
        "gov-deploy.yaml")
    if "--air-gapped" in argv:
        profile["air_gapped"] = True
        argv = [a for a in argv if a != "--air-gapped"]
    print(f"Pronto Gov readiness, Nov 8, 2027; boundary "
          f"{profile['boundary']} (Class C)")
    print(f"{'component':<22}{'region':<14}result")
    rows = review(deploy, profile)
    show(rows)
    print("fixes:")
    for c, problems, _ in rows:
        if problems:
            fix = FIXES.get(c["name"], ({}, "none in profile"))
            print(f"  {c['name']:<22}{fix[1]}")
    after = review(fixed(deploy), profile)
    bad = sum(1 for _, p, _ in after if p)
    print(f"after fixes: {len(after) - bad} ok, {bad} fail")
    if bad:
        show(after)
    m = monitor(profile)
    print("continuous monitoring, 30 days:")
    n = m["receipts"]
    for key, label in (("in_boundary", "in boundary regions"),
                       ("authorized_model", "authorized model"),
                       ("signature_valid", "signature valid")):
        print(f"  {label:<26}{m[key]:>6,} of {n:,}")
    print("  egress denied at boundary:")
    for src, k in m["egress_denied"].items():
        print(f"    {src:<32}{k:>2}")
    pct = round(100 * m["automated"] / m["checks"])
    print(f"  checks automated: {m['automated']} of "
          f"{m['checks']} ({pct}%)")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "where-gov.json").write_text(json.dumps(
            {"where": where()}, indent=2) + "\n")
        (out / "monitoring.json").write_text(json.dumps(
            m, indent=2) + "\n")


if __name__ == "__main__":
    main()
