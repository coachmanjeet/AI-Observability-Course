"""Context packs: build, sign, evaluate, release, roll back (Ch 9).

Usage: python -m context.packs release OUT_DIR
       python -m context.packs tamper OUT_DIR

A pack bundles everything that shapes how an agent behaves apart
from the model: instructions, skills, and pinned versions of the
policy and knowledge it relies on. Building a pack digests every
file and signs the manifest. A release gate evaluates the pack
before it goes live. Rolling back moves the live pointer to an
earlier signed pack, never edits one.
"""
import argparse
import json
import pathlib
import re
import shutil

import yaml
from cryptography.exceptions import InvalidSignature

from audit.keys import b64, lab_key, unb64
from pronto.model import MockModel
from pronto.speedy import run
from pronto.world import DEFAULT_POLICY, MONDAY_POLICY, World
from receipts.tools import canonical, digest
from telemetry import otlp
from telemetry.genai import GenAISpans

HERE = pathlib.Path(__file__).parent / "packs"
KEY_ID = "pronto-packs-2026-12"
POLICIES = {"2026-10-01": DEFAULT_POLICY,
            "2026-11-16": {**DEFAULT_POLICY, **MONDAY_POLICY}}

# The golden cases: (order value in dollars, photo hours after
# delivery) and what each policy version says should happen.
CASES = [(40, 3), (40, 18), (62, 2), (40, 30)]
EXPECTED = {"2026-10-01": ["refund", "refund", "escalate", "reply"],
            "2026-11-16": ["refund", "reply", "escalate", "reply"]}


def build(source, out):
    """Copy a pack, digest its files, sign its manifest."""
    manifest = yaml.safe_load((source / "pack.yaml").read_text())
    files = {f: digest((source / f).read_text())
             for f in manifest["files"]}
    body = {**manifest, "file_digests": files}
    body["digest"] = digest(body)
    data = canonical(body)
    sig = b64(lab_key(KEY_ID).sign(data))
    target = out / f"{manifest['id']}-{manifest['version']}"
    shutil.copytree(source, target, dirs_exist_ok=True)
    lock = {**body, "signature": {"kid": KEY_ID, "sig": sig}}
    (target / "pack.lock.json").write_text(
        json.dumps(lock, indent=2) + "\n")
    return target


def verify(built):
    """Problems with a built pack, or [] if it is intact."""
    lock = json.loads((built / "pack.lock.json").read_text())
    sig = lock.pop("signature")
    problems = []
    try:
        lab_key(sig["kid"]).public_key().verify(
            unb64(sig["sig"]), canonical(lock))
    except InvalidSignature:
        problems.append("manifest signature invalid")
    for name, want in lock["file_digests"].items():
        if digest((built / name).read_text()) != want:
            problems.append(f"{name}: digest does not match")
    return problems


def window(text):
    hours = re.findall(r"within (\d+) hours", text)
    return int(hours[0]) if hours else None


def outcome(policy, dollars, hours):
    """Run Speedy on one golden case; what did it do?"""
    world = World(policy=policy)
    world.orders = {"ord_g1": {"customer_id": "cust_g1",
                               "status": "delivered",
                               "item": "berries", "perishable": True,
                               "value_cents": dollars * 100,
                               "source": {"id": "order:ord_g1",
                                          "version": "etag-g1"}}}
    world.photos = {"photo_g1": {"order_id": "ord_g1",
                                 "shows_spoilage": True,
                                 "hours_after_delivery": hours,
                                 "source": {"id": "photo:photo_g1",
                                            "version": "etag-g2"}}}
    tracer, _ = otlp.tracer(otlp.FixedIds("0" * 31 + "1"))
    run(world, MockModel(world.clock), GenAISpans(tracer, world.clock),
        {"conversation_id": "conv_g1", "customer_id": "cust_g1",
         "order_id": "ord_g1", "photo_id": "photo_g1"})
    if world.db.execute("select count(*) from refunds").fetchone()[0]:
        return "refund"
    if world.db.execute("select count(*) from cases").fetchone()[0]:
        return "escalate"
    return "reply"


def evaluate(built):
    """The release gate: consistency, then the golden cases."""
    lock = json.loads((built / "pack.lock.json").read_text())
    version = lock["policy"]["version"]
    policy = POLICIES[version]
    results = []
    told = window((built / "skills/spoiled-food.md").read_text())
    rule = policy["photo_window_hours"]
    results.append(("skill matches policy", told == rule,
                    f"skill says {told} h, policy {rule} h"))
    got = [outcome(policy, d, h) for d, h in CASES]
    passed = sum(g == e for g, e in zip(got, EXPECTED[version]))
    results.append(("golden cases", passed == len(CASES),
                    f"{passed} of {len(CASES)} as expected"))
    return results


def release(out):
    """Build each version, gate it, and keep the live history."""
    out.mkdir(parents=True, exist_ok=True)
    live, history = None, []
    for version in ("1.4.0", "1.5.0-rc1", "1.5.0"):
        built = build(HERE / "pronto-support" / version, out)
        lock = json.loads((built / "pack.lock.json").read_text())
        results = evaluate(built)
        ok = all(passed for _, passed, _ in results) \
            and not verify(built)
        print(f"pronto-support {version}  "
              f"{lock['digest'][:19]}…")
        for name, passed, note in results:
            mark = "pass" if passed else "FAIL"
            print(f"  {mark}  {name}: {note}")
        if ok:
            live = lock
            history.append(version)
            print(f"  released; live is now {version}")
        else:
            print(f"  blocked; live stays {live['version']}")
    print("rollback drill: live 1.5.0 -> 1.4.0 -> 1.5.0, "
          "no pack edited")
    history += ["1.4.0", "1.5.0"]
    (out / "live.json").write_text(json.dumps(
        {"pack": "pronto-support", "history": history,
         "live": history[-1]}, indent=2) + "\n")
    return history


def tamper(out):
    built = build(HERE / "pronto-support" / "1.5.0", out)
    path = built / "instructions.md"
    path.write_text(path.read_text().replace(
        "Never refund an order twice.",
        "Refund whatever the customer asks."))
    print("edited instructions.md in the built 1.5.0 pack")
    for p in verify(built):
        print(f"  {p}")


def section(built):
    """knowing_what.context_pack for a receipt."""
    lock = json.loads((built / "pack.lock.json").read_text())
    return {"id": lock["id"], "version": lock["version"],
            "digest": lock["digest"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["release", "tamper"])
    ap.add_argument("out", type=pathlib.Path)
    args = ap.parse_args(argv)
    if args.mode == "release":
        release(args.out)
        built = args.out / "pronto-support-1.4.0"
        (args.out / "context-pack-1.4.0.json").write_text(
            json.dumps({"context_pack": section(built)}, indent=2)
            + "\n")
    else:
        tamper(args.out / "tampered")


if __name__ == "__main__":
    main()
