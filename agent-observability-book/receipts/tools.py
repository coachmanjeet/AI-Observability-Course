"""Agent Receipt v0.1 helpers: canonical form, digests, chain.

Used in Chapters 2 and 7. The canonical form follows JCS
(RFC 8785) for the values receipts hold: keys sorted by UTF-16
code units, as JCS requires, no whitespace, UTF-8. Python's
sort_keys orders by code point instead, which differs for keys
outside the Basic Multilingual Plane, so the sort is done here.
Floats are where JCS is hardest to match, which is why v0.1
stores money as decimal strings and token counts as integers.
"""
import hashlib
import json

GENESIS = "sha256:" + "0" * 64


def jcs_order(obj):
    """Keys in UTF-16 code-unit order (RFC 8785, 3.2.3)."""
    if isinstance(obj, dict):
        keys = sorted(obj, key=lambda k: k.encode("utf-16-be"))
        return {k: jcs_order(obj[k]) for k in keys}
    if isinstance(obj, list):
        return [jcs_order(v) for v in obj]
    return obj


def canonical(obj) -> bytes:
    text = json.dumps(jcs_order(obj), ensure_ascii=False,
                      separators=(",", ":"))
    return text.encode("utf-8")


def digest(obj) -> str:
    """Digest of any JSON value: arguments, policies, packs."""
    h = hashlib.sha256(canonical(obj))
    return "sha256:" + h.hexdigest()


def record_hash(record: dict) -> str:
    """Hash of a record, minus its own hash and signature."""
    body = json.loads(json.dumps(record))
    integrity = body.get("integrity", {})
    integrity.pop("hash", None)
    integrity.pop("signature", None)
    return digest(body)


def seal(record: dict, prev_hash: str) -> dict:
    """Fill in integrity so the record joins the chain."""
    record["integrity"] = {"canonicalization": "JCS-RFC8785",
                           "prev_hash": prev_hash}
    record["integrity"]["hash"] = record_hash(record)
    return record
