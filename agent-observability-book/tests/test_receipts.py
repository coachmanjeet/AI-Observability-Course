"""Chapter 2: the Agent Receipt schema, validator and hash chain."""
import json
import pathlib
import subprocess
import sys

from receipts.tools import GENESIS, seal
from receipts.validate import check

EXAMPLES = pathlib.Path(__file__).parent.parent / "receipts" / "examples"
CHAIN = [EXAMPLES / n for n in ("01-speedy-order-lookup.json", "02-speedy-refund-40.json", "03-outcome-refund-40.json")]
NIGHT_OWL = EXAMPLES / "04-night-owl-refund-85-R1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(tmp_path, name, record):
    path = tmp_path / name
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_chain_passes_and_answers_all_seven(capsys):
    assert check(CHAIN)
    out = capsys.readouterr().out
    assert out.count("answers 7/7, chained") == 2
    assert "outcome achieved, chained" in out


def test_night_owl_answers_two_of_seven(capsys):
    assert check([NIGHT_OWL])
    out = capsys.readouterr().out
    assert "R1, answers 2/7, unchained" in out
    assert " ".join(out.split()).endswith(
        "cannot answer: for whom, knowing what, under which rule, "
        "at what cost, where")


def test_tampered_amount_breaks_the_hash(tmp_path, capsys):
    refund = load(CHAIN[1])
    refund["did_what"]["effect"]["amount"]["value"] = "400.00"
    assert not check([CHAIN[0], write(tmp_path, "02-tampered.json", refund)])
    assert "hash does not match; record altered" in capsys.readouterr().out


def test_dropped_record_breaks_the_chain(capsys):
    assert not check([CHAIN[0], CHAIN[2]])          # outcome without the refund it resolves
    assert "prev_hash breaks the chain" in capsys.readouterr().out


def test_r4_without_where_fails_even_when_resealed(tmp_path, capsys):
    refund = load(CHAIN[1])
    del refund["where"]
    seal(refund, load(CHAIN[0])["integrity"]["hash"])  # a valid hash cannot hide a missing answer
    assert not check([CHAIN[0], write(tmp_path, "02-no-where.json", refund)])
    assert "'where' is a required property" in capsys.readouterr().out


def test_r2_requires_for_whom(tmp_path):
    owl = load(NIGHT_OWL)
    owl["conformance"] = "R2"                         # claiming a level you can't back up fails
    assert not check([write(tmp_path, "owl-r2.json", owl)])


def test_raw_floats_are_rejected(tmp_path):
    refund = load(CHAIN[1])
    refund["did_what"]["effect"]["amount"]["value"] = 40.0
    seal(refund, GENESIS)
    assert not check([write(tmp_path, "float.json", refund)])


def test_committed_examples_match_the_builder(tmp_path):
    subprocess.run([sys.executable, "-m", "receipts.build_examples", str(tmp_path)],
                   check=True, capture_output=True, cwd=EXAMPLES.parent.parent)
    for path in [*CHAIN, NIGHT_OWL]:
        assert load(tmp_path / path.name) == load(path), f"{path.name} is stale; rerun make receipt"
