"""Builds Pronto's receipt store for one night, then attacks it.

Usage: python -m audit.run [--attacks] OUT_DIR

Used in Chapter 7. Reruns Chapter 6's night of 1,000 conversations,
builds a receipt for every consequential action (before any trace
sampling), appends them to a signed, hash-chained store with one
writer, writes a checkpoint, and verifies the chain. --attacks then
tampers with copies of the store four ways and verifies each.
"""
import argparse
import json
import pathlib
import shutil

from audit.keys import lab_key
from audit.store import ReceiptStore, sign, verify
from collector.night import night
from receipts.from_trace import load_inventory, receipts
from receipts.tools import record_hash
from telemetry import otlp

ROOT = pathlib.Path(__file__).parent.parent
CHECKPOINT_AT = "2026-11-14T06:00:00Z"


def night_receipts(tmp):
    """Every consequential action of the night, as a receipt."""
    spans, _ = night()
    otlp.write(spans, tmp / "night.json")
    loaded = otlp.load(tmp / "night.json")
    inventory = load_inventory(ROOT / "maturity" / "fleet.json")
    return list(receipts(loaded, inventory, with_cost=True))


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    path = out / "tenant-pronto.jsonl"
    path.unlink(missing_ok=True)
    store = ReceiptStore(path, lab_key())
    for rec in night_receipts(out):
        store.append(rec)
    cp = store.checkpoint(CHECKPOINT_AT)
    (out / "checkpoint.json").write_text(json.dumps(cp, indent=2))
    lines = path.read_text().splitlines()
    sample = lines[first(lines, "refunds.create")]
    (out / "sample-refund.json").write_text(sample)
    return path, cp


def rewrite(path, edit):
    lines = path.read_text().splitlines()
    lines = edit(lines)
    path.write_text("".join(line + "\n" for line in lines))


def first(lines, tool):
    """Index of the first succeeded receipt for this tool."""
    for i, line in enumerate(lines):
        rec = json.loads(line)
        if rec["did_what"]["action"]["tool"] == tool and \
                rec["did_what"]["effect"]["status"] == "succeeded":
            return i
    raise LookupError(tool)


def raise_refund(lines, rehash=False, resign=None):
    i = first(lines, "refunds.create")
    rec = json.loads(lines[i])
    rec["did_what"]["effect"]["amount"]["value"] = "400.00"
    if rehash:
        rec["integrity"]["hash"] = record_hash(rec)
    if resign:
        rec["integrity"]["signature"] = sign(
            resign, rec["integrity"]["hash"])
    lines[i] = json.dumps(rec, sort_keys=True)
    return lines


def attacks(path, cp):
    """Four ways to tamper with the store, and what verify says."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    stolen = Ed25519PrivateKey.from_private_bytes(bytes(32))
    cases = [
        ("edit a refund to $400", raise_refund),
        ("edit it and recompute its hash",
         lambda ls: raise_refund(ls, rehash=True)),
        ("edit, rehash, sign with another key",
         lambda ls: raise_refund(ls, True, stolen)),
        ("delete one receipt",
         lambda ls: ls[:first(ls, "cases.escalate")]
         + ls[first(ls, "cases.escalate") + 1:]),
        ("cut the last 12 receipts", lambda ls: ls[:-12])]
    public = lab_key().public_key()
    for name, edit in cases:
        copy = path.with_name("tampered.jsonl")
        shutil.copy(path, copy)
        rewrite(copy, edit)
        _, problems = verify(copy, public, cp)
        print(f"{name}:")
        for p in problems[:2]:
            print(f"  {p}")
        copy.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--attacks", action="store_true")
    args = parser.parse_args(argv)
    path, cp = build(args.out)
    size = path.stat().st_size
    n, problems = verify(path, lab_key().public_key(), cp)
    print(f"appended {n:,} receipts to {path.name}")
    print(f"store: {size / 1e6:.1f} MB, {size // n:,} bytes a receipt")
    print(f"checkpoint: {cp['count']:,} records, head "
          f"{cp['head'][:19]}…")
    print(f"verify: {n:,} records, {len(problems)} problems")
    if args.attacks:
        print()
        attacks(path, cp)


if __name__ == "__main__":
    main()
