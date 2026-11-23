"""Chapter 12: workload identity for agents."""
import json

from identity.workload import (GW, LAPTOP, NOW, SPEEDY, TTL,
                               attest, verify)


def test_speedy_attests_and_verifies():
    token, why = attest(SPEEDY, GW)
    assert why == "issued"
    sub, ok = verify(token, GW)
    assert ok == "ok" and sub.endswith("/agent/speedy")


def test_tokens_are_short_lived():
    token, _ = attest(SPEEDY, GW)
    assert verify(token, GW, NOW + TTL - 1)[1] == "ok"
    assert verify(token, GW, NOW + TTL)[1] == "expired"


def test_tokens_are_for_one_audience():
    token, _ = attest(SPEEDY, GW)
    assert verify(token, "payments.pronto.example")[1] == \
        "wrong audience"


def test_no_entry_no_identity():
    assert attest(LAPTOP, GW) == (None,
                                  "no registration entry matches")


def test_a_changed_image_gets_no_identity():
    other = {**SPEEDY, "image": "sha256:0bad"}
    assert attest(other, GW)[0] is None


def test_workload_id_matches_chapter_2():
    token, _ = attest(SPEEDY, GW)
    sub, _ = verify(token, GW)
    ex = json.loads(open("receipts/examples/"
                         "02-speedy-refund-40.json").read())
    assert sub == ex["who"]["workload_id"]
