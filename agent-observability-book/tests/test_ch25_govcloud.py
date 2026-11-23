"""Chapter 25: Gov Cloud configuration profile."""
import json

from comply.govcloud import (check, fixed, load, main, monitor,
                             review)

PROFILE = load("gov-profile.yaml")
DEPLOY = load("gov-deploy.yaml")


def failing(rows):
    return {c["name"]: p for c, p, _ in rows if p}


def test_readiness_finds_four_crossings():
    bad = failing(review(DEPLOY, PROFILE))
    assert bad == {"fallback model": ["model"],
                   "context pack registry": ["region", "fips"],
                   "trace export": ["region", "fips"],
                   "eval judge": ["region", "fips", "model"]}


def test_in_progress_model_is_not_authorized():
    c = {"name": "x", "region": "us-gov-west-1", "fips": True,
         "model": "model-c", "updates": "managed"}
    assert check(c, PROFILE)[0] == ["model"]


def test_retirement_is_flagged():
    c = DEPLOY[1]
    assert check(c, PROFILE)[1] == ["model-a retires in 114d"]


def test_unapproved_signature_algorithm():
    c = {**DEPLOY[8], "alg": "HS256"}
    assert check(c, PROFILE)[0] == ["alg"]


def test_fixes_clear_the_review():
    assert failing(review(fixed(DEPLOY), PROFILE)) == {}


def test_air_gapped_needs_no_path_out():
    gapped = {**PROFILE, "air_gapped": True}
    bad = failing(review(fixed(DEPLOY), gapped))
    assert set(bad) == {"model endpoint", "fallback model",
                        "eval judge", "receipt signing key"}


def test_monitoring_is_mostly_automated():
    m = monitor(PROFILE)
    assert m["in_boundary"] == m["receipts"]
    assert m["automated"] / m["checks"] >= 0.8


def test_where_inside_the_boundary(tmp_path):
    main([str(tmp_path)])
    w = json.loads((tmp_path / "where-gov.json").read_text())
    assert w["where"]["region"].startswith("us-gov-")
    assert w["where"]["model_endpoint_region"].startswith(
        "us-gov-")
