"""Builds R1 receipts from an agent trace (Chapter 4).

Usage: python -m receipts.from_trace TRACE.json OUT_DIR
           [--inventory maturity/fleet.json]

Each execute_tool span for a consequential tool becomes one receipt.
The trace answers two of the seven questions: who acted, from the
invoke_agent span above the tool call, and doing what, from the tool
span. The inventory adds the agent's kind and owner. An agent missing
from the inventory is a shadow agent. When the trace records decision
links (Chapter 5), it answers a third: knowing what.
"""
import argparse
import contextlib
import io
import json
import pathlib
from datetime import datetime, timezone

from collector.prices import model_cost
from pronto.sources import describe
from pronto.tools import TOOLS
from receipts.validate import check, unanswered
from telemetry import otlp
from telemetry.lint import ancestors

KIND = {"1P": "first_party", "3P": "third_party", "shadow": "shadow"}


def iso(ns):
    t = datetime.fromtimestamp(ns // 1_000_000_000, tz=timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def who(agent_span, inventory):
    a = agent_span["attributes"]
    known = inventory.get(a["gen_ai.agent.id"])
    return {"agent_id": a["gen_ai.agent.id"],
            "agent_name": a["gen_ai.agent.name"],
            "agent_version": a["gen_ai.agent.version"],
            "kind": KIND[known["kind"]] if known else "shadow",
            "owner": (known or {}).get("owner") or "unknown",
            "runtime": agent_span["resource"]["service.name"]}


def effect(a):
    out = {"status": a.get("pronto.effect.status", "succeeded")}
    if "pronto.effect.ref" in a:
        out["external_ref"] = a["pronto.effect.ref"]
    if "pronto.effect.amount" in a:
        out["amount"] = {"value": a["pronto.effect.amount"],
                         "currency": a["pronto.effect.currency"]}
    return out


def wire(span, children):
    """How the call left the agent: (action fields, evidence fields)."""
    for child in children.get(span["span_id"], []):
        a = child["attributes"]
        if "mcp.method.name" in a:
            return ({"via": "mcp", "mcp_method": a["mcp.method.name"]},
                    {"mcp_session_id": a["mcp.session.id"]})
        if a.get("gen_ai.operation.name") == "invoke_agent":
            return {"via": "a2a"}, {}
        if a.get("messaging.operation.type") == "send":
            return {"via": "queue"}, {}
    return {"via": "direct"}, {}


def linked(span, by_id, kind):
    """Spans this span links to with pronto.link == kind."""
    return [by_id[link["span_id"]] for link in span["links"]
            if link["attributes"].get("pronto.link") == kind
            and link["span_id"] in by_id]


def knowing(s, by_id):
    """Chapter 5: the model call that asked for this tool call, and
    the versioned records that were in its context."""
    asked = linked(s, by_id, "decided_by")
    if not asked:
        return None
    a = asked[0]["attributes"]
    model = {"provider": a["gen_ai.provider.name"],
             "request_model": a["gen_ai.request.model"]}
    if "gen_ai.response.model" in a:
        model["response_model"] = a["gen_ai.response.model"]
    sources = []
    for read in linked(asked[0], by_id, "in_context"):
        r = read["attributes"]
        if "gen_ai.data_source.id" not in r:
            continue
        entry = describe(r["gen_ai.data_source.id"])
        sources.append({"id": r["gen_ai.data_source.id"],
                        **({"uri": entry["uri"]} if entry else {}),
                        "version": r["pronto.source.version"],
                        "retrieved_at": iso(read["end"]),
                        **{k: entry[k] for k in ("authority",
                                                 "sensitivity",
                                                 "origin", "trust")
                           if k in entry}})
    return {"model": model, "sources": sources}


def cost(s, by_id):
    """Chapter 6: the cost of the model call that decided this action.
    Meters (billable) are Chapter 22's, so the list starts empty."""
    asked = linked(s, by_id, "decided_by")
    if not asked:
        return None
    a = asked[0]["attributes"]
    tokens = {"input": a["gen_ai.usage.input_tokens"],
              "output": a["gen_ai.usage.output_tokens"]}
    cached = a.get("gen_ai.usage.cache_read.input_tokens")
    if cached is not None:
        tokens["cache_read"] = cached
    value = model_cost(a["gen_ai.request.model"], tokens["input"],
                       tokens["output"], cached or 0)
    return {"tokens": tokens,
            "model_cost": {"value": value, "currency": "USD"},
            "billable": []}


def receipt(s, tool, who_, wire_fields, evidence_extra, known=None,
            priced=None):
    a = s["attributes"]
    action = {"operation": "execute_tool",
              "tool": a["gen_ai.tool.name"]}
    if "gen_ai.tool.call.id" in a:
        action["tool_call_id"] = a["gen_ai.tool.call.id"]
    action.update(wire_fields)
    action.update({"target": a["pronto.tool.target"],
                   "arguments_digest": a["pronto.tool.arguments_digest"]})
    evidence = {"trace_id": s["trace_id"], "span_id": s["span_id"]}
    if "gen_ai.conversation.id" in a:
        evidence["conversation_id"] = a["gen_ai.conversation.id"]
    evidence.update(evidence_extra)
    rec = {
        "receipt_version": "0.1",
        "receipt_id": f"rcpt_{s['trace_id'][:8]}{s['span_id']}",
        "issued_at": iso(s["end"]),
        "conformance": "R1",
        "consequence": {"side_effect": tool.side_effect,
                        "reason": tool.reason},
        "who": who_}
    if known:
        rec["knowing_what"] = known
    rec.update({
        "did_what": {"action": action, "effect": effect(a),
                     "outcome": {"status": "unknown",
                                 "metric": "not_defined"}}})
    if priced:
        rec["at_what_cost"] = priced
    rec["evidence"] = evidence
    return rec


def consequential(s):
    tool = TOOLS.get(s["attributes"].get("gen_ai.tool.name"))
    return tool if tool and tool.side_effect else None


def receipts(spans, inventory, with_cost=False):
    """One receipt per consequential action, written from the most
    complete span this backend holds: the agent's own tool span for
    Pronto's agents, the MCP server span for anyone else's."""
    by_id = {s["span_id"]: s for s in spans}
    children = {}
    for s in spans:
        children.setdefault(s["parent_id"], []).append(s)
    handoffs = {}                    # remote trace ID -> receipt ID
    for s in spans:
        a, tool = s["attributes"], consequential(s)
        if a.get("gen_ai.operation.name") != "execute_tool" or not tool \
                or "mcp.method.name" in a:
            continue
        agent = next(p for p in ancestors(s, by_id) if p["attributes"]
                     .get("gen_ai.operation.name") == "invoke_agent")
        wire_fields, extra = wire(s, children)
        rec = receipt(s, tool, who(agent, inventory), wire_fields, extra,
                      knowing(s, by_id),
                      cost(s, by_id) if with_cost else None)
        for child in children.get(s["span_id"], []):
            remote = child["attributes"].get("pronto.a2a.remote_trace_id")
            if remote:
                handoffs[remote] = rec["receipt_id"]
        yield rec
    for s in spans:                  # calls from agents we don't run
        a, tool = s["attributes"], consequential(s)
        if s["kind"] != "SERVER" or not tool or s["parent_id"] in by_id:
            continue
        extra = {"mcp_session_id": a["mcp.session.id"]}
        if s["trace_id"] in handoffs:
            extra["parent_receipt_id"] = handoffs[s["trace_id"]]
        yield receipt(s, tool, caller(s, inventory),
                      {"via": "mcp", "mcp_method": a["mcp.method.name"]},
                      extra)


def caller(server_span, inventory):
    """Who called, as the MCP session claims it (Chapter 12 makes this
    a verified identity instead of a claim)."""
    a = server_span["attributes"]
    known = inventory.get(a["pronto.mcp.client.agent_id"], {})
    return {"agent_id": a["pronto.mcp.client.agent_id"],
            "agent_name": a["pronto.mcp.client.name"],
            "agent_version": "unknown",
            "kind": KIND[known["kind"]] if known else "shadow",
            "owner": known.get("owner") or "unknown",
            "runtime": server_span["resource"]["service.name"]}


def load_inventory(path):
    fleet = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return {agent["agent_id"]: agent for agent in fleet["agents"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("trace")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--inventory", default="maturity/fleet.json")
    parser.add_argument("--cost", action="store_true",
                        help="Chapter 6: price each decision's model call")
    parser.add_argument("--brief", action="store_true",
                        help="one line per receipt instead of the "
                        "validator's report")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    inventory = load_inventory(args.inventory)
    paths = []
    found = receipts(otlp.load(args.trace), inventory, args.cost)
    for n, rec in enumerate(found, 1):
        tool = rec["did_what"]["action"]["tool"].replace(".", "-")
        path = args.out / f"{n:02d}-{tool}.json"
        path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    if not args.brief:
        return 0 if check(paths) else 1
    with contextlib.redirect_stdout(io.StringIO()):
        ok = check(paths)
    answers = {7 - len(unanswered(json.loads(p.read_text())))
               for p in paths}
    counts = " to ".join(str(n) for n in sorted(answers))
    print(f"PASS {len(paths)} receipts, each R1 with {counts} of 7 "
          "answers" if ok else
          f"FAIL {len(paths)} receipts; rerun without --brief")
    ids = {}
    for n, path in enumerate(paths, 1):
        rec = json.loads(path.read_text(encoding="utf-8"))
        ids[rec["receipt_id"]] = n
        who, act = rec["who"]["agent_name"], rec["did_what"]["action"]
        print(f"{n:02d} {who:<7} {act['tool']:<15} via "
              f"{act['via']:<6} trace {rec['evidence']['trace_id'][:8]}")
        parent = rec["evidence"].get("parent_receipt_id")
        if parent:
            print(f"   parent receipt: {ids.get(parent, 0):02d}, "
                  f"{rec['who']['kind'].replace('_', '-')} caller")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
