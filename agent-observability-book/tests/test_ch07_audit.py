"""Chapter 7: the signed receipt store, and replay."""
import json

import pytest

from audit.keys import lab_key
from audit.replay import inputs, recorded, rerun
from audit.run import build, night_receipts, raise_refund, rewrite
from audit.snapshots import snapshots
from audit.store import ReceiptStore, verify
from receipts.validate import RECEIPT
from telemetry import otlp


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    return build(tmp_path_factory.mktemp("audit"))


def test_the_night_chain_verifies(store):
    path, cp = store
    n, problems = verify(path, lab_key().public_key(), cp)
    assert (n, problems) == (1170, [])


def test_sealed_receipts_still_match_the_schema(store):
    path, _ = store
    first = json.loads(path.read_text().splitlines()[0])
    assert not list(RECEIPT.iter_errors(first))


def test_an_edit_is_caught(store, tmp_path):
    path, cp = store
    copy = tmp_path / "t.jsonl"
    copy.write_text(path.read_text())
    rewrite(copy, raise_refund)
    _, problems = verify(copy, lab_key().public_key(), cp)
    assert "record altered" in problems[0]


def test_a_rehashed_edit_fails_the_signature(store, tmp_path):
    path, cp = store
    copy = tmp_path / "t.jsonl"
    copy.write_text(path.read_text())
    rewrite(copy, lambda ls: raise_refund(ls, rehash=True))
    _, problems = verify(copy, lab_key().public_key(), cp)
    assert "signature invalid" in problems[0]


def test_truncation_needs_the_checkpoint(store, tmp_path):
    path, cp = store
    copy = tmp_path / "t.jsonl"
    copy.write_text(path.read_text())
    rewrite(copy, lambda ls: ls[:-12])
    public = lab_key().public_key()
    assert verify(copy, public)[1] == []
    assert "truncated" in verify(copy, public, cp)[1][0]


def test_reopening_the_store_continues_the_chain(tmp_path):
    rec = json.loads(open(
        "receipts/examples/04-night-owl-refund-85-R1.json").read())
    path = tmp_path / "s.jsonl"
    ReceiptStore(path, lab_key()).append(rec)
    ReceiptStore(path, lab_key()).append(rec)
    assert verify(path, lab_key().public_key()) == (2, [])


def test_replay_needs_the_model_not_only_the_inputs(tmp_path):
    recs = night_receipts(tmp_path)
    spans = otlp.load(tmp_path / "night.json")
    blocked = [r for r in recs
               if r["did_what"]["effect"]["status"] == "blocked"
               and r["did_what"]["action"]["tool"] == "refunds.create"]
    assert len(blocked) == 3
    r, snaps = blocked[0], snapshots()
    seen = inputs(spans, r)
    assert seen["policy:refunds"] == "2026-10-01"
    assert rerun(seen, snaps, r) == "cases.escalate succeeded"
    assert rerun(seen, snaps, r, careless=True) == recorded(r)
