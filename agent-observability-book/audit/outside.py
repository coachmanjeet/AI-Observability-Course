"""What a customer can verify with only the pack (Chapter 24).

Usage: python -m audit.outside OUT_DIR

Builds Chapter 7's signed store, then makes the pack Pronto sends
Fresca: 25 refund receipts drawn at random, the writer's public
key and the latest signed checkpoint. A separate verifier reads
only those files and reports which claims they support. Then it
repeats the check with the chain segment, the extra evidence a
stronger claim needs.

The point is the difference. Signatures prove each sampled record
came from Pronto's writer and hasn't changed. The checkpoint
proves what the writer said about the chain's length and head.
Neither connects 25 scattered records to that checkpoint, and
neither shows that nothing is missing in between.
"""
import json
import pathlib
import random
import sys

from cryptography.hazmat.primitives import serialization

from audit.keys import lab_key
from audit.run import build
from audit.store import checkpoint_ok, signature_ok, verify
from receipts.tools import record_hash

SAMPLE, SEED = 25, 2027


def make_pack(out):
    """The files Fresca receives, and nothing else."""
    path, cp = build(out / "store")
    lines = path.read_text().splitlines()
    refunds = [line for line in lines
               if json.loads(line)["did_what"]["action"]["tool"]
               == "refunds.create"]
    picked = sorted(random.Random(SEED).sample(
        range(len(refunds)), SAMPLE))
    pack = out / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "sample.jsonl").write_text(
        "".join(refunds[i] + "\n" for i in picked))
    (pack / "checkpoint.json").write_text(json.dumps(cp, indent=2))
    (pack / "public-key.pem").write_bytes(
        lab_key().public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
    return pack, path, len(refunds)


def check_pack(pack):
    """Fresca's verifier: reads only the pack's three files."""
    public = serialization.load_pem_public_key(
        (pack / "public-key.pem").read_bytes())
    cp = json.loads((pack / "checkpoint.json").read_text())
    recs = [json.loads(line) for line in
            (pack / "sample.jsonl").read_text().splitlines()]
    signed = sum(record_hash(r) == r["integrity"]["hash"]
                 and signature_ok(public, r["integrity"]["signature"],
                                  r["integrity"]["hash"])
                 for r in recs)
    linked = sum(b["integrity"]["prev_hash"] == a["integrity"]["hash"]
                 for a, b in zip(recs, recs[1:]))
    return {"n": len(recs), "signed": signed,
            "checkpoint": checkpoint_ok(public, cp),
            "count": cp["count"], "linked": linked,
            "pairs": len(recs) - 1, "public": public, "cp": cp,
            "hashes": {r["integrity"]["hash"] for r in recs}}


def with_segment(result, chain):
    """The stronger check: the chain up to the checkpoint, read
    under an authorized verification, finds every sample in it."""
    n, problems = verify(chain, result["public"], result["cp"])
    held = {json.loads(line)["integrity"]["hash"]
            for line in chain.read_text().splitlines()}
    return n, problems, len(result["hashes"] & held)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = pathlib.Path(argv[0] if argv else "build/outside")
    pack, chain, refunds = make_pack(out)
    r = check_pack(pack)
    print(f"Fresca's check, pack files only ({r['n']} of "
          f"{refunds} refunds)")
    print(f"  signatures        {r['signed']} of {r['n']} valid: "
          "Pronto's writer, unaltered")
    print(f"  checkpoint        "
          f"{'valid' if r['checkpoint'] else 'INVALID'}: "
          f"{r['count']:,} records")
    print(f"  links in sample   {r['linked']} of {r['pairs']} "
          "pairs adjacent")
    print("  in the chain      not provable from the pack")
    print("  none missing      not provable from the pack")
    n, problems, found = with_segment(r, chain)
    print("With the chain segment, authorized verification")
    print(f"  chain             {n:,} records, "
          f"{len(problems)} problems, to the checkpoint")
    print(f"  samples in chain  {found} of {r['n']}")
    print("  none missing      needs the ledger: Chapter 7's join")


if __name__ == "__main__":
    main()
