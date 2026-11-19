"""Agent Receipt v0.1 helpers: canonical form, digests, hash chain.

Used in Chapters 2 and 8. The canonical form approximates JCS
(RFC 8785): sorted keys, no whitespace, UTF-8. It matches JCS exactly
as long as records hold no floats, which is why v0.1 stores money as
decimal strings and token counts as integers.
"""
import hashlib
import json

GENESIS = "sha256:" + "0" * 64


def canonical(obj) -> bytes:
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False,
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
