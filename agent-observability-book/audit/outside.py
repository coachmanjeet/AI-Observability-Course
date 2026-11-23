"""What a customer can verify with the pack (Chapter 24).

Usage: python -m audit.outside OUT_DIR

Builds Chapter 7's signed store, then makes the pack Pronto sends
Fresca: 25 refund receipts drawn at random, the writer's public
key and the latest signed checkpoint. Fresca also holds records of
its own that didn't come in the pack: the key's fingerprint from
the signed contract, and checkpoints it fetched itself from
Pronto's published feed. A separate verifier reads only those
files and reports which claims they support. Then it repeats the
check with the chain segment, the extra evidence a stronger claim
needs.

Signatures prove each sampled record came from the key, and the
contract's fingerprint proves the key is Pronto's. The checkpoint
proves what the writer said about the chain's length and head, and
Fresca's own copies show it is current and hasn't shrunk. None of
that connects 25 scattered records to the checkpoint, or shows
that nothing between them is missing.
"""
import hashlib
import json
import pathlib
import random
import sys
from datetime import datetime, timedelta

from cryptography.hazmat.primitives import serialization

from audit.keys import KEY_ID, b64, lab_key, unb64
from audit.run import build
from audit.store import HEADER, checkpoint_ok, signature_ok, verify
from receipts.tools import canonical, record_hash

SAMPLE, SEED = 25, 2027
ISSUED = "2026-11-14T09:00:00Z"      # when the pack was assembled
MAX_AGE = timedelta(hours=24)        # agreed in the contract
EARLIER = 1040                       # the checkpoint Fresca kept


def fingerprint(public):
    der = public.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo)
    return "sha256:" + hashlib.sha256(der).hexdigest()


def signed_checkpoint(key, body):
    """A checkpoint as the writer signs it (audit.store)."""
    payload = b64(canonical(body))
    sig = key.sign(f"{HEADER}.{payload}".encode())
    return {**body, "signature": f"{HEADER}.{payload}.{b64(sig)}"}


def when(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def make_pack(out):
    """The pack's files, and Fresca's own records, kept apart."""
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
    (pack / "pack.json").write_text(json.dumps(
        {"issued_at": ISSUED, "sample": SAMPLE}, indent=2))
    public = lab_key().public_key()
    (pack / "public-key.pem").write_bytes(public.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo))
    # Fresca's own records: the contract, and what it fetched itself
    own = out / "fresca"
    own.mkdir(parents=True, exist_ok=True)
    (own / "contract-key.json").write_text(json.dumps(
        {"kid": KEY_ID, "fingerprint": fingerprint(public),
         "source": "MSA exhibit C, signed by both parties"},
        indent=2))
    (own / "feed-latest.json").write_text(json.dumps(cp, indent=2))
    head = json.loads(lines[EARLIER - 1])["integrity"]["hash"]
    earlier = signed_checkpoint(lab_key(), {
        "chain": cp["chain"], "count": EARLIER, "head": head,
        "at": "2026-11-14T05:45:00Z"})
    (own / "kept-checkpoint.json").write_text(
        json.dumps(earlier, indent=2))
    return pack, own, path, len(refunds)


def kid(jws):
    return json.loads(unb64(jws.split(".")[0]))["kid"]


def check_pack(pack, own):
    """Fresca's verifier: the pack's files and Fresca's own."""
    public = serialization.load_pem_public_key(
        (pack / "public-key.pem").read_bytes())
    cp = json.loads((pack / "checkpoint.json").read_text())
    issued = when(json.loads(
        (pack / "pack.json").read_text())["issued_at"])
    contract = json.loads((own / "contract-key.json").read_text())
    feed = json.loads((own / "feed-latest.json").read_text())
    kept = json.loads((own / "kept-checkpoint.json").read_text())
    recs = [json.loads(line) for line in
            (pack / "sample.jsonl").read_text().splitlines()]
    key_ok = (fingerprint(public) == contract["fingerprint"]
              and kid(cp["signature"]) == contract["kid"]
              and all(kid(r["integrity"]["signature"])
                      == contract["kid"] for r in recs))
    signed = sum(record_hash(r) == r["integrity"]["hash"]
                 and signature_ok(public, r["integrity"]["signature"],
                                  r["integrity"]["hash"])
                 for r in recs)
    age = issued - when(cp["at"])
    current = (checkpoint_ok(public, feed)
               and feed["head"] == cp["head"]
               and feed["count"] == cp["count"]
               and age <= MAX_AGE
               and checkpoint_ok(public, kept)
               and cp["count"] >= kept["count"])
    linked = sum(b["integrity"]["prev_hash"] == a["integrity"]["hash"]
                 for a, b in zip(recs, recs[1:]))
    return {"n": len(recs), "key": key_ok, "signed": signed,
            "checkpoint": checkpoint_ok(public, cp),
            "count": cp["count"], "age": age, "current": current,
            "kept": kept, "linked": linked,
            "pairs": len(recs) - 1, "public": public, "cp": cp,
            "hashes": {r["integrity"]["hash"] for r in recs}}


def with_segment(result, chain):
    """The stronger check: the chain up to the checkpoint, read
    under an authorized verification, finds every sample in it and
    the head of the checkpoint Fresca kept earlier."""
    n, problems = verify(chain, result["public"], result["cp"])
    hashes = [json.loads(line)["integrity"]["hash"]
              for line in chain.read_text().splitlines()]
    kept = result["kept"]
    grew = hashes[kept["count"] - 1] == kept["head"]
    return n, problems, len(result["hashes"] & set(hashes)), grew


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = pathlib.Path(argv[0] if argv else "build/outside")
    pack, own, chain, refunds = make_pack(out)
    r = check_pack(pack, own)
    hours = int(r["age"].total_seconds() // 3600)
    yes = {True: "", False: "FAILED: "}
    print(f"Fresca's check, the pack and its own records "
          f"({r['n']} of {refunds})")
    print(f"  key               {yes[r['key']]}fingerprint and kid "
          "match the contract")
    print(f"  signatures        {r['signed']} of {r['n']} valid: "
          "Pronto's writer, unaltered")
    print(f"  checkpoint        "
          f"{'valid' if r['checkpoint'] else 'INVALID'}: "
          f"{r['count']:,} records, {hours} h old at issue")
    print(f"  current           {yes[r['current']]}same as the feed;"
          f" up from {r['kept']['count']:,} kept")
    print(f"  links in sample   {r['linked']} of {r['pairs']} "
          "pairs adjacent")
    print("  in the chain      not provable from the pack")
    print("  none missing      not provable from the pack")
    n, problems, found, grew = with_segment(r, chain)
    print("With the chain segment, authorized verification")
    print(f"  chain             {n:,} records, "
          f"{len(problems)} problems, to the checkpoint")
    print(f"  kept checkpoint   "
          f"{'head at' if grew else 'MISSING at'} record "
          f"{r['kept']['count']:,}: the chain only grew")
    print(f"  samples in chain  {found} of {r['n']}")
    print("  none missing      needs the ledger: Chapter 7's join")


if __name__ == "__main__":
    main()
