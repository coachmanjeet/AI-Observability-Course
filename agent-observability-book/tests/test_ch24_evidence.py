"""Chapter 24: the evidence pack."""
import json

import pytest
import yaml

from comply.evidence import CHECKS, HERE, MIN_DAYS, pack


@pytest.fixture(scope="module")
def rows():
    return pack()


def test_every_requirement_has_a_check(rows):
    req = yaml.safe_load((HERE / "crosswalk.yaml").read_text())
    assert all(r["check"] in CHECKS for r in req)
    assert len(rows) == len(req) == 16


def test_counts(rows):
    s = [r["status"] for r in rows]
    assert (s.count("met"), s.count("partial"),
            s.count("gap")) == (13, 2, 1)


def test_the_gap_is_the_impact_assessment(rows):
    gaps = [r["id"] for r in rows if r["status"] == "gap"]
    assert gaps == ["A.5.2"]


def test_retention_meets_six_months():
    days = yaml.safe_load((HERE / "retention.yaml").read_text())
    assert days["receipts"] >= MIN_DAYS


def test_one_check_serves_several_frameworks(rows):
    by = {}
    for r in rows:
        by.setdefault(r["check"], set()).add(r["fw"])
    assert by["receipts"] == {"EU AI Act", "ISO 42001"}
    assert by["monitoring"] == {"ISO 42001", "NIST AI RMF",
                                "SOC 2"}


def test_tampered_receipt_fails_the_log_check(tmp_path):
    from receipts.tools import record_hash
    ex = json.loads((HERE.parent / "receipts" / "examples" /
                     "02-speedy-refund-40.json").read_text())
    ex["did_what"]["effect"]["amount"]["value"] = "400.00"
    assert record_hash(ex) != ex["integrity"]["hash"]
