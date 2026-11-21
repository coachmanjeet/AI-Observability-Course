"""Chapter 23: durable, multi-modal workflows."""
import pytest

from orchestration.durable import (Bridge, Payments, Run, execute,
                                   receipts, route_workflow)


def world():
    return {"bridge": Bridge(2), "payments": Payments()}


def test_crashes_do_not_repeat_side_effects():
    w = world()
    history, log = execute(w, ["timer", "credit"])
    assert [e["step"] for e in history] == [
        "vision", "voice-customer", "timer", "voice-driver",
        "credit"]
    assert len(w["payments"].credits) == 1
    assert w["payments"].attempts == 2
    assert len(w["bridge"].calls) == 2


def test_replay_returns_recorded_results():
    w = world()
    history, _ = execute(w, [])
    run = Run(history, world())
    route_workflow(run)
    assert run.replayed == 5 and run.effects == 0


def test_changed_code_is_caught_on_replay():
    w = world()
    history, _ = execute(w, [])
    history[0]["step"] = "ocr"
    with pytest.raises(AssertionError):
        route_workflow(Run(history, world()))


def test_bridge_v2_carries_trace_context():
    w = world()
    execute(w, [])
    assert all(c["traceparent"] for c in w["bridge"].calls)
    v1 = Bridge(1)
    v1.call("customer", "x", "00-a-b-01")
    assert v1.calls[0]["traceparent"] is None


def test_each_step_has_its_own_trace():
    history, _ = execute(world(), [])
    assert len({e["trace_id"] for e in history}) == 5


def test_receipts_chain_across_hours():
    history, _ = execute(world(), ["credit"])
    rec = receipts(history)
    assert len(rec) == 3
    assert "parent_receipt_id" not in rec[0]["evidence"]
    for a, b in zip(rec, rec[1:]):
        assert b["evidence"]["parent_receipt_id"] == \
            a["receipt_id"]
    assert {r["evidence"]["conversation_id"] for r in rec} == \
        {"wf_7c21"}
