"""An append-only, hash-chained, signed receipt store (Chapter 8).

One writer per tenant chain. Each record is sealed with the hash of
the record before it, signed with a detached JWS (EdDSA over the
record's hash), and written as one JSON line. Checkpoints sign the
chain's length and head, so a copy kept elsewhere can prove that
nothing was cut off the end.
"""
import json
import pathlib

from cryptography.exceptions import InvalidSignature

from audit.keys import KEY_ID, b64, unb64
from receipts.tools import GENESIS, canonical, record_hash, seal

HEADER = b64(canonical({"alg": "EdDSA", "kid": KEY_ID,
                        "b64": True}))


def sign(key, record_hash_):
    """Detached JWS: header..signature, payload is the hash."""
    data = f"{HEADER}.{b64(record_hash_.encode())}".encode()
    return f"{HEADER}..{b64(key.sign(data))}"


def signature_ok(public, jws, record_hash_):
    header, _, sig = jws.split(".")
    data = f"{header}.{b64(record_hash_.encode())}".encode()
    try:
        public.verify(unb64(sig), data)
        return True
    except InvalidSignature:
        return False


class ReceiptStore:
    """The single writer for one tenant's chain."""

    def __init__(self, path, key):
        self.path, self.key = pathlib.Path(path), key
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.head, self.count = GENESIS, 0
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                self.head = json.loads(line)["integrity"]["hash"]
                self.count += 1

    def append(self, record):
        record = seal(json.loads(json.dumps(record)), self.head)
        record["integrity"]["signature"] = sign(
            self.key, record["integrity"]["hash"])
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        self.head, self.count = record["integrity"]["hash"], \
            self.count + 1
        return record

    def checkpoint(self, at):
        """A signed statement of the chain's length and head."""
        body = {"chain": self.path.name, "count": self.count,
                "head": self.head, "at": at}
        payload = b64(canonical(body))
        data = f"{HEADER}.{payload}".encode()
        return {**body, "signature":
                f"{HEADER}.{payload}.{b64(self.key.sign(data))}"}


def verify(path, public, checkpoint=None):
    """Walk the chain. Returns (records checked, problems)."""
    problems, prev, n = [], GENESIS, 0
    lines = pathlib.Path(path).read_text().splitlines()
    for n, line in enumerate(lines, 1):
        rec = json.loads(line)
        integ = rec["integrity"]
        if record_hash(rec) != integ["hash"]:
            problems.append(f"record {n}: hash does not match; "
                            "record altered")
        elif not signature_ok(public, integ["signature"],
                              integ["hash"]):
            problems.append(f"record {n}: signature invalid; "
                            "not the receipt writer's key")
        if integ["prev_hash"] != prev:
            problems.append(f"record {n}: prev_hash mismatch; "
                            "record missing or reordered")
        prev = integ["hash"]
    if checkpoint:
        if not checkpoint_ok(public, checkpoint):
            problems.append("checkpoint signature invalid")
        elif n < checkpoint["count"]:
            problems.append(f"truncated: checkpoint says "
                            f"{checkpoint['count']} records, "
                            f"store has {n}")
        elif json.loads(lines[checkpoint["count"] - 1])[
                "integrity"]["hash"] != checkpoint["head"]:
            problems.append("record at the checkpoint does not "
                            "match its head; history rewritten")
    return n, problems


def checkpoint_ok(public, cp):
    header, payload, sig = cp["signature"].split(".")
    body = {k: v for k, v in cp.items() if k != "signature"}
    if unb64(payload) != canonical(body):
        return False
    try:
        public.verify(unb64(sig), f"{header}.{payload}".encode())
        return True
    except InvalidSignature:
        return False
