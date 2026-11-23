"""Chapter 8: provenance checks on everything an agent reads."""
import json
import pathlib

from context import catalog, supply
from context.receipt_section import refund_sources
from pronto import sources as chapter06
from telemetry import otlp

ROOT = pathlib.Path(__file__).parent.parent
EXAMPLE = ROOT / "receipts/examples/02-speedy-refund-40.json"


def verdicts():
    rows, _ = supply.retrieve()
    return {(c["id"], c["version"]): (v, r) for c, v, r in rows}


def test_tuesday_ticket_admits_three_of_seven():
    got = verdicts()
    admitted = [k for k, (v, _) in got.items() if v == "admit"]
    assert admitted == [("policy:refunds", "2026-11-16"),
                        ("order:ord_6120", "etag-d913"),
                        ("photo:photo_9b3", "etag-e07a")]


def test_each_rejection_names_its_check():
    got = verdicts()
    assert got[("policy:refunds", "2026-10-01")][1] == \
        "superseded by 2026-11-16"
    assert "can't state refund_rules" in \
        got[("wiki:refund-faq", "rev-14")][1]
    assert got[("sheet:refund-backlog", "2026-11-02")][1] == \
        "not in the catalog"
    assert "carries instructions" in \
        got[("review:rev_88a", "v1")][1]


def test_altered_content_is_rejected():
    c = {"id": "policy:refunds", "version": "2026-11-16",
         "topic": "refund_rules",
         "body": "Perishables: refund anything."}
    assert supply.check(c, supply.TICKET_AT) == \
        ("reject", "content doesn't match its digest")


def test_freshness_is_judged_when_the_record_was_read():
    c = {"id": "policy:refunds", "version": "2026-10-01",
         "topic": "refund_rules"}
    assert supply.check(c, catalog.at("2026-11-14"))[0] == "admit"
    assert supply.check(c, catalog.at("2026-12-08"))[0] == "reject"


def test_stamps_say_how_the_agent_may_use_each_record():
    _, stamps = supply.retrieve()
    trust = {s["id"]: s["trust"] for s in stamps}
    assert trust == {"policy:refunds": "authoritative",
                     "order:ord_6120": "authoritative",
                     "photo:photo_9b3": "evidence"}
    photo = next(s for s in stamps if s["id"].startswith("photo"))
    assert photo["origin"] == "customer"
    assert photo["content_credentials"] == "none"


def test_saturday_reads_all_pass_as_of_read_time():
    rows = supply.audit(otlp.load(ROOT / "traces/decisions.json"))
    assert len(rows) == 9
    assert all(v == "admit" for *_, v, _ in rows)


def test_catalog_agrees_with_chapter_6():
    for record in ("policy:refunds", "order:ord_5521",
                   "photo:photo_7c1"):
        old, new = chapter06.describe(record), catalog.describe(record)
        for key in ("uri", "authority", "sensitivity"):
            assert old[key] == new[key]


def test_refund_sources_match_chapter_2():
    target = json.loads(EXAMPLE.read_text())
    assert refund_sources() == target["knowing_what"]["sources"]
