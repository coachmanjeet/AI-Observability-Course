"""Chapter 24: what a recipient can verify with only the pack."""
import pytest

from audit import outside


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp("outside")
    pack, chain, _ = outside.make_pack(out)
    return pack, chain, outside.check_pack(pack)


def test_the_pack_holds_three_files(result):
    pack, _, _ = result
    assert sorted(p.name for p in pack.iterdir()) == [
        "checkpoint.json", "public-key.pem", "sample.jsonl"]


def test_every_sampled_signature_verifies(result):
    _, _, r = result
    assert r["signed"] == r["n"] == outside.SAMPLE
    assert r["checkpoint"]


def test_a_scattered_sample_does_not_link(result):
    _, _, r = result
    assert r["linked"] < r["pairs"] / 4


def test_the_segment_connects_every_sample(result):
    _, chain, r = result
    n, problems, found = outside.with_segment(r, chain)
    assert not problems and n == r["count"]
    assert found == r["n"]
