"""Chapter 5: one conversation across MCP, A2A and a queue."""
import json
import pathlib

import pytest

import pronto.mcp
from pronto.handoffs import TRACES, conversation
from pronto.run import TRACE_40
from receipts.from_trace import load_inventory, receipts
from telemetry import otlp
from telemetry.lint import lint

ROOT = pathlib.Path(__file__).parent.parent
EXAMPLES = ROOT / "receipts" / "examples"
INVENTORY = load_inventory(ROOT / "maturity" / "fleet.json")


@pytest.fixture
def run(tmp_path):
    pronto, payco, replies = conversation()
    otlp.write(pronto, tmp_path / "pronto.json")
    otlp.write(payco, tmp_path / "payco.json")
    return (otlp.load(tmp_path / "pronto.json"),
            otlp.load(tmp_path / "payco.json"), replies)


def named(spans, name, kind=None):
    return [s for s in spans if s["name"] == name
            and (kind is None or s["kind"] == kind)]


def test_mcp_keeps_one_trace(run):
    pronto, _, replies = run
    assert replies[0] == "Done! I've refunded $40.00."
    by_id = {s["span_id"]: s for s in pronto}
    server, = [s for s in named(pronto, "tools/call refunds.create", "SERVER")]
    client = by_id[server["parent_id"]]
    tool = by_id[client["parent_id"]]
    assert server["trace_id"] == client["trace_id"] == TRACE_40
    assert client["kind"] == "CLIENT" and tool["name"] == "execute_tool refunds.create"
    assert server["resource"]["service.name"] == "pronto-commerce-mcp"
    assert server["attributes"]["mcp.session.id"] == "mcps_19c4850a"


def test_context_crosses_only_in_meta(monkeypatch, tmp_path):
    monkeypatch.setattr(pronto.mcp, "inject", lambda carrier: carrier)
    spans, _, _ = conversation()                     # _meta has no traceparent
    otlp.write(spans, tmp_path / "broken.json")
    loaded = otlp.load(tmp_path / "broken.json")
    server, = named(loaded, "tools/call refunds.create", "SERVER")
    assert server["parent_id"] is None and server["trace_id"] != TRACE_40
    _, findings = lint(loaded)
    assert [(lvl, s["name"]) for lvl, s, _ in findings if lvl == "E"] == [
        ("E", "tools/call orders.get"), ("E", "tools/call refunds.create")]


def test_a2a_partner_links_instead_of_joining(run):
    pronto, payco, replies = run
    assert "dp_4410" in replies[1]
    client, = named(pronto, "invoke_agent Ledger", "CLIENT")
    ledger, = named(payco, "invoke_agent Ledger")
    assert ledger["trace_id"] == TRACES["payco"] != client["trace_id"]
    assert ledger["links"] == [{"trace_id": client["trace_id"],
                                "span_id": client["span_id"],
                                "attributes": {"pronto.link": "a2a_caller"}}]
    assert client["attributes"]["pronto.a2a.remote_trace_id"] == TRACES["payco"]


def test_queue_worker_links_to_the_producer(run):
    pronto, _, _ = run
    send, = named(pronto, "send notifications")
    process, = named(pronto, "process notifications")
    assert send["kind"] == "PRODUCER" and process["kind"] == "CONSUMER"
    assert process["trace_id"] == TRACES["notify"] and process["parent_id"] is None
    assert process["links"] == [{"trace_id": send["trace_id"],
                                 "span_id": send["span_id"],
                                 "attributes": {}}]
    assert (process["start"] - send["end"]) / 1e9 > 60


def test_lint_treats_a_partners_parent_as_a_warning(run):
    _, findings = lint(run[0])
    assert [(level, msg) for level, _, msg in findings] == [
        ("W", "remote parent is in another backend")]


def test_one_receipt_per_acting_agent(run):
    built = list(receipts(run[0], INVENTORY))
    assert [(r["who"]["agent_name"], r["did_what"]["action"]["via"])
            for r in built] == [("Speedy", "mcp"), ("Speedy", "mcp"),
                                ("Speedy", "queue"), ("Speedy", "a2a"),
                                ("Ledger", "mcp")]
    handoff, ledger_read = built[3], built[4]
    assert ledger_read["who"]["kind"] == "third_party"
    assert ledger_read["evidence"]["parent_receipt_id"] == handoff["receipt_id"]
    assert ledger_read["evidence"]["trace_id"] == TRACES["payco"]


def test_refund_receipt_now_matches_chapter_2_exactly(run):
    built = {r["did_what"]["action"]["tool"]: r
             for r in receipts(run[0], INVENTORY)
             if r["who"]["agent_name"] == "Speedy"}
    for tool, name in [("orders.get", "01-speedy-order-lookup.json"),
                       ("refunds.create", "02-speedy-refund-40.json")]:
        target = json.loads((EXAMPLES / name).read_text())
        rec = built[tool]
        assert rec["issued_at"] == target["issued_at"]
        assert rec["did_what"]["action"] == target["did_what"]["action"]
        assert rec["evidence"] == target["evidence"]


def test_unknown_caller_is_a_shadow(run):
    ledger_read = list(receipts(run[0], inventory={}))[-1]
    assert ledger_read["who"]["kind"] == "shadow"


def test_committed_conversation_is_current(run):
    for name, spans in [("pronto", run[0]), ("payco", run[1])]:
        committed = otlp.load(ROOT / "traces" / f"handoff-{name}.json")
        assert committed == spans, f"stale {name} trace; rerun make handoff"


def _server(sampler=None):
    from pronto.mcp import McpServer
    from pronto.world import World
    tracer, exported = otlp.tracer(otlp.FixedIds(TRACE_40),
                                   sampler=sampler)
    return McpServer(World(), tracer, ["orders.get"]), exported


def _wire(tool, flags):
    meta = {"traceparent": f"00-{'ab' * 16}-{'cd' * 8}-{flags}",
            "pronto.example/client": {"id": "mcps_x", "name": "Night Owl",
                                      "agent_id": "agent://unknown"}}
    return json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "_meta": meta,
                                  "arguments": {"order_id": "ord_5521"}}})


def test_caller_cannot_switch_off_the_servers_record():
    server, exported = _server()                 # the SDK default
    server.handle(_wire("orders.get", "00"))     # "not sampled"
    assert exported.get_finished_spans() == ()
    server, exported = _server(pronto.mcp.RECORD_EVERY_CALL)
    server.handle(_wire("orders.get", "00"))
    span, = exported.get_finished_spans()
    assert f"{span.context.trace_id:032x}" == "ab" * 16


def test_server_refuses_tools_it_does_not_serve():
    server, exported = _server(pronto.mcp.RECORD_EVERY_CALL)
    reply = json.loads(server.handle(_wire("refunds.create", "01")))
    assert reply["error"]["code"] == -32602
    assert exported.get_finished_spans() == ()
