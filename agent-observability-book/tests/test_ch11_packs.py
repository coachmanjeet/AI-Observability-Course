"""Chapter 11: signed, evaluated, versioned context packs."""
import json

from context.packs import (HERE, build, evaluate, release, section,
                           verify)


def test_a_built_pack_verifies(tmp_path):
    built = build(HERE / "pronto-support" / "1.5.0", tmp_path)
    assert verify(built) == []


def test_an_edited_file_is_caught(tmp_path):
    built = build(HERE / "pronto-support" / "1.5.0", tmp_path)
    (built / "skills/spoiled-food.md").write_text("anything goes")
    assert verify(built) == ["skills/spoiled-food.md: digest does "
                             "not match"]


def test_the_gate_blocks_a_skill_that_drifted(tmp_path):
    built = build(HERE / "pronto-support" / "1.5.0-rc1", tmp_path)
    first = evaluate(built)[0]
    assert first[1] is False and "24 h, policy 12 h" in first[2]


def test_golden_cases_follow_each_policy(tmp_path):
    for v in ("1.4.0", "1.5.0"):
        built = build(HERE / "pronto-support" / v, tmp_path)
        assert all(ok for _, ok, _ in evaluate(built))


def test_release_skips_the_blocked_candidate(tmp_path, capsys):
    history = release(tmp_path)
    assert history == ["1.4.0", "1.5.0", "1.4.0", "1.5.0"]
    live = json.loads((tmp_path / "live.json").read_text())
    assert live["live"] == "1.5.0"


def test_receipt_section_matches_chapter_2(tmp_path):
    built = build(HERE / "pronto-support" / "1.4.0", tmp_path)
    ex = json.loads(open("receipts/examples/"
                         "02-speedy-refund-40.json").read())
    want = ex["knowing_what"]["context_pack"]
    got = section(built)
    assert (got["id"], got["version"]) == (want["id"],
                                           want["version"])
    assert got["digest"].startswith("sha256:")
