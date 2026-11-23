"""Chapter 5: decision links, versioned sources and the graph."""
import json
import pathlib

import pytest

from decisions.graph import used, why
from decisions.run import turns
from pronto.run import TRACE_40, trace_turn, REFUND_40
from receipts.from_trace import load_inventory, receipts
from telemetry import otlp

ROOT = pathlib.Path(__file__).parent.parent
EXAMPLE = json.loads((ROOT / "receipts" / "examples" /
                      "02-speedy-refund-40.json").read_text())
INVENTORY = load_inventory(ROOT / "maturity" / "fleet.json")


@pytest.fixture(scope="module")
def spans(tmp_path_factory):
    out = tmp_path_factory.mktemp("decisions") / "decisions.json"
    otlp.write(turns()[0], out)
    return otlp.load(out)


def kind(link):
    return link["attributes"]["pronto.link"]


def test_tool_calls_link_to_the_model_call_that_asked(spans):
    by_id = {s["span_id"]: s for s in spans}
    refund = next(s for s in spans if s["name"] ==
                  "execute_tool refunds.create" and
                  s["trace_id"] == TRACE_40)
    link, = refund["links"]
    asked = by_id[link["span_id"]]
    assert kind(link) == "decided_by" and asked["name"].startswith("chat")
    assert asked["end"] <= refund["start"]
    seen = [by_id[l["span_id"]]["name"] for l in asked["links"]]
    assert seen == ["execute_tool orders.get",
                    "execute_tool policy.lookup",
                    "execute_tool photos.verify"]
    assert {kind(l) for l in asked["links"]} == {"in_context"}


def test_reads_record_source_and_version(spans):
    reads = {s["attributes"]["gen_ai.data_source.id"]:
             s["attributes"]["pronto.source.version"]
             for s in spans if "gen_ai.data_source.id" in s["attributes"]}
    assert reads["policy:refunds"] == "2026-11-16"     # Monday wins
    assert reads["order:ord_5521"] == "etag-9f2c"
    assert reads["photo:photo_7c1"] == "etag-41c7"


def test_receipt_knows_what_chapter_2_says(spans):
    refund = next(r for r in receipts(spans, INVENTORY)
                  if r["evidence"]["span_id"] == "00f067aa0ba902b7")
    expected = EXAMPLE["knowing_what"]
    assert refund["knowing_what"]["model"] == expected["model"]
    assert refund["knowing_what"]["sources"] == expected["sources"]


def test_why_and_used(spans):
    text = why(spans, "order:ord_5521")
    assert "policy:refunds   2026-10-01  policy.lookup  02:06:45" in text
    assert "knew only the customer's message" in text
    assert "6 of 6 actions have a decision trace" in text
    report = used(spans, "policy:refunds")
    assert "policy:refunds @ 2026-10-01: 2 actions" in report
    assert "policy:refunds @ 2026-11-16: 1 action" in report
    assert used(spans, "photo:photo_7c1").count("refund:rf_9931") == 1


def test_decision_links_are_opt_in():
    _, plain = trace_turn(REFUND_40)
    assert all(not s.links for s in plain)


def test_committed_decisions_trace_is_current(spans):
    committed = otlp.load(ROOT / "traces" / "decisions.json")
    assert committed == spans
