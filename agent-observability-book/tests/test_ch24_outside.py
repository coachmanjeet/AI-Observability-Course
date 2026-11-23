"""Chapter 24: what a recipient can verify with the pack."""
import json

import pytest

from audit import outside


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    out = tmp_path_factory.mktemp("outside")
    pack, own, chain, _ = outside.make_pack(out)
    return pack, own, chain, outside.check_pack(pack, own)


def test_the_pack_and_frescas_records_are_apart(made):
    pack, own, _, _ = made
    assert sorted(p.name for p in pack.iterdir()) == [
        "checkpoint.json", "pack.json", "public-key.pem",
        "sample.jsonl"]
    assert sorted(p.name for p in own.iterdir()) == [
        "contract-key.json", "feed-latest.json",
        "kept-checkpoint.json"]


def test_every_sampled_signature_verifies(made):
    _, _, _, r = made
    assert r["signed"] == r["n"] == outside.SAMPLE
    assert r["checkpoint"] and r["key"] and r["current"]


def test_a_key_the_contract_doesnt_name_fails(made, tmp_path):
    pack, own, _, _ = made
    fake = tmp_path / "fresca"
    fake.mkdir()
    for f in own.iterdir():
        (fake / f.name).write_text(f.read_text())
    c = json.loads((fake / "contract-key.json").read_text())
    c["fingerprint"] = "sha256:" + "0" * 64
    (fake / "contract-key.json").write_text(json.dumps(c))
    assert not outside.check_pack(pack, fake)["key"]


def test_a_stale_or_shrunken_checkpoint_is_not_current(made,
                                                         tmp_path):
    pack, own, _, _ = made
    old = tmp_path / "pack"
    old.mkdir()
    for f in pack.iterdir():
        (old / f.name).write_bytes(f.read_bytes())
    (old / "pack.json").write_text(json.dumps(
        {"issued_at": "2026-11-16T09:00:00Z", "sample": 25}))
    assert not outside.check_pack(old, own)["current"]   # 51 h old
    big = json.loads((own / "kept-checkpoint.json").read_text())
    big["count"] = 5000
    fresh = tmp_path / "own"
    fresh.mkdir()
    for f in own.iterdir():
        (fresh / f.name).write_text(f.read_text())
    (fresh / "kept-checkpoint.json").write_text(json.dumps(big))
    assert not outside.check_pack(pack, fresh)["current"]


def test_a_scattered_sample_does_not_link(made):
    _, _, _, r = made
    assert r["linked"] < r["pairs"] / 4


def test_the_segment_connects_every_sample(made):
    _, _, chain, r = made
    n, problems, found, grew = outside.with_segment(r, chain)
    assert not problems and n == r["count"]
    assert found == r["n"] and grew
