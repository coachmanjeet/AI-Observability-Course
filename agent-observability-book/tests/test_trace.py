"""Chapter 4: Speedy's instrumented trace, the linter and R1 receipts."""
import json
import pathlib

import pytest

from pronto.run import REFUND_40, REFUND_85, SPANS_40, TRACE_40, trace_turn
from receipts.from_trace import load_inventory, receipts
from receipts.validate import check
from telemetry import otlp
from telemetry.lint import lint

ROOT = pathlib.Path(__file__).parent.parent
EXAMPLES = ROOT / "receipts" / "examples"
INVENTORY = load_inventory(ROOT / "maturity" / "fleet.json")


@pytest.fixture
def refund(tmp_path):
    reply, spans = trace_turn(REFUND_40, span_ids=SPANS_40)
    otlp.write(spans, tmp_path / "t.json")
    return reply, otlp.load(tmp_path / "t.json")


def ops(spans, op):
    return [s for s in spans
            if s["attributes"]["gen_ai.operation.name"] == op]


def test_one_turn_is_one_tree(refund):
    reply, spans = refund
    assert reply == "Done! I've refunded $40.00."
    root, = ops(spans, "invoke_agent")
    assert root["parent_id"] is None and root["name"] == "invoke_agent Speedy"
    assert {s["trace_id"] for s in spans} == {TRACE_40}
    children = [s for s in spans if s is not root]
    assert all(s["parent_id"] == root["span_id"] for s in children)
    assert len(ops(spans, "chat")) == 4 and len(ops(spans, "execute_tool")) == 4


def test_spans_follow_the_conventions(refund):
    _, spans = refund
    for s in ops(spans, "chat"):
        a = s["attributes"]
        assert s["kind"] == "CLIENT" and s["name"] == "chat pronto-mock-1"
        assert a["gen_ai.provider.name"] == "mock"
        assert a["gen_ai.usage.cache_read.input_tokens"] == 1800
    for s in ops(spans, "execute_tool"):
        assert s["kind"] == "INTERNAL"
        assert s["name"] == "execute_tool " + s["attributes"]["gen_ai.tool.name"]
    tokens = sum(s["attributes"]["gen_ai.usage.input_tokens"]
                 for s in ops(spans, "chat"))
    assert tokens == 11480


def test_parallel_tool_calls_share_one_model_response(refund):
    _, spans = refund
    names = [s["attributes"]["gen_ai.tool.name"] for s in ops(spans, "execute_tool")]
    assert names == ["orders.get", "policy.lookup", "photos.verify",
                     "refunds.create"]


def test_lint_passes_clean_trace(refund):
    genai, findings = lint(refund[1])
    assert len(genai) == 9 and findings == []


def test_lint_catches_broken_spans(refund):
    _, spans = refund
    tool = ops(spans, "execute_tool")[-1]
    tool["attributes"].pop("pronto.tool.target")
    tool["parent_id"] = "ffffffffffffffff"            # orphaned
    chat = ops(spans, "chat")[0]
    chat["attributes"]["gen_ai.system"] = "mock"       # deprecated name
    messages = {msg for _, _, msg in lint(spans)[1]}
    assert "parent span is missing from the trace" in messages
    assert "no invoke_agent span above it" in messages
    assert "consequential, but not receipt-ready" in messages
    assert "uses gen_ai.system; emit gen_ai.provider.name" in messages


def test_content_capture_is_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT",
                       "true")
    _, spans = trace_turn(REFUND_40, span_ids=SPANS_40)
    otlp.write(spans, tmp_path / "c.json")
    loaded = otlp.load(tmp_path / "c.json")
    refund_span = ops(loaded, "execute_tool")[-1]
    args = json.loads(refund_span["attributes"]["gen_ai.tool.call.arguments"])
    assert args["amount"] == "40.00"                   # content is in the trace
    assert any("captures content" in msg for _, _, msg in lint(loaded)[1])


def test_receipts_from_trace_match_chapter_2(refund, tmp_path):
    built = list(receipts(refund[1], INVENTORY))
    assert [r["did_what"]["action"]["tool"] for r in built] == [
        "orders.get", "refunds.create"]
    for rec, name in zip(built, ["01-speedy-order-lookup.json",
                                 "02-speedy-refund-40.json"]):
        target = json.loads((EXAMPLES / name).read_text())
        assert rec["issued_at"] == target["issued_at"]
        assert rec["consequence"] == target["consequence"]
        assert rec["who"].items() <= target["who"].items()
        for key in ("operation", "tool", "tool_call_id", "target",
                    "arguments_digest"):
            assert rec["did_what"]["action"][key] == target["did_what"]["action"][key]
        for key in ("trace_id", "span_id", "conversation_id"):
            assert rec["evidence"][key] == target["evidence"][key]
    refund_effect = json.loads((EXAMPLES / "02-speedy-refund-40.json").read_text())
    effect = refund_effect["did_what"]["effect"]
    assert built[1]["did_what"]["effect"] == {
        k: effect[k] for k in ("status", "external_ref", "amount")}
    paths = []
    for n, rec in enumerate(built):
        paths.append(tmp_path / f"{n}.json")
        paths[-1].write_text(json.dumps(rec))
    assert check(paths)                                # valid R1


def test_agent_missing_from_inventory_is_shadow(refund):
    rec = next(receipts(refund[1], inventory={}))
    assert rec["who"]["kind"] == "shadow" and rec["who"]["owner"] == "unknown"


def test_refund_tool_blocks_a_careless_model(tmp_path):
    reply, spans = trace_turn(REFUND_85, careless=True,
                              trace_id="0af7651916cd43dd8448eb211c80319c")
    otlp.write(spans, tmp_path / "c.json")
    loaded = otlp.load(tmp_path / "c.json")
    refund_span = ops(loaded, "execute_tool")[-1]
    assert refund_span["status"] == 2
    assert refund_span["attributes"]["error.type"] == "ApprovalRequired"
    rec = list(receipts(loaded, INVENTORY))[-1]
    assert rec["did_what"]["effect"] == {"status": "blocked"}
    assert "couldn't" in reply


def test_careful_model_escalates_over_50(tmp_path):
    reply, spans = trace_turn(REFUND_85,
                              trace_id="0af7651916cd43dd8448eb211c80319c")
    otlp.write(spans, tmp_path / "e.json")
    tools = [s["attributes"]["gen_ai.tool.name"]
             for s in ops(otlp.load(tmp_path / "e.json"), "execute_tool")]
    assert tools[-1] == "cases.escalate" and "teammate" in reply


def test_committed_trace_is_current(refund):
    committed = otlp.load(ROOT / "traces" / "speedy-refund-40.json")
    assert committed == refund[1], "stale trace; rerun make trace"
