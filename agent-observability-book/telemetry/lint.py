"""Checks an agent trace against the GenAI conventions (Chapter 4).

Usage: python -m telemetry.lint TRACE.json [--strict]

Works on any OTLP JSON file, from this repo or from a Collector's file
exporter, so you can check what your own framework emits. Errors break
the conventions. Warnings mark spans a receipt can't be built from.
Exit code 1 on errors, or on warnings with --strict.
"""
import argparse
import pathlib
import sys
import textwrap

from pronto.tools import TOOLS
from telemetry import otlp
from telemetry.waterfall import plural

CONTENT = ["gen_ai.input.messages", "gen_ai.output.messages",
           "gen_ai.system_instructions", "gen_ai.tool.call.arguments",
           "gen_ai.tool.call.result"]
DEPRECATED = {"gen_ai.system": "gen_ai.provider.name",
              "gen_ai.usage.prompt_tokens": "gen_ai.usage.input_tokens",
              "gen_ai.usage.completion_tokens":
                  "gen_ai.usage.output_tokens"}
MODEL_OPS = ("chat", "text_completion", "generate_content")


def ancestors(span, by_id):
    while span["parent_id"] in by_id:
        span = by_id[span["parent_id"]]
        yield span


def check_span(s, by_id):
    """Yield (level, message) findings for one GenAI or MCP span."""
    a = s["attributes"]
    op, method = a.get("gen_ai.operation.name"), a.get("mcp.method.name")
    for old, new in DEPRECATED.items():
        if old in a:
            yield "E", f"uses {old}; emit {new}"
    if s["parent_id"] and s["parent_id"] not in by_id:
        if s["kind"] in ("SERVER", "CONSUMER"):
            yield "W", "remote parent is in another backend"
        else:
            yield "E", "parent span is missing from the trace"
    if method:                                   # MCP (Chapter 4)
        tool = a.get("gen_ai.tool.name")
        expected = f"{method} {tool}" if tool else method
        if s["name"] != expected:
            yield "E", f"span name should be '{expected}'"
        if s["kind"] not in ("CLIENT", "SERVER"):
            yield "E", "kind should be CLIENT or SERVER"
        if "mcp.session.id" not in a:
            yield "W", "no mcp.session.id"
        if s["kind"] == "SERVER" and _not_receipt_ready(a):
            yield "W", "consequential, but not receipt-ready"
    elif op == "invoke_agent":
        name = a.get("gen_ai.agent.name")
        if not name:
            yield "E", "names no agent (gen_ai.agent.name)"
        elif s["name"] != f"invoke_agent {name}":
            yield "E", f"span name should be 'invoke_agent {name}'"
        if s["kind"] not in ("INTERNAL", "CLIENT"):
            yield "E", "kind should be INTERNAL or CLIENT"
        for key in ("gen_ai.agent.id", "gen_ai.agent.version",
                    "gen_ai.conversation.id"):
            if key not in a:
                yield "W", f"no {key}; a receipt needs it"
    elif op in MODEL_OPS:
        if "gen_ai.provider.name" not in a:
            yield "E", "no gen_ai.provider.name"
        model = a.get("gen_ai.request.model")
        if model and s["name"] != f"{op} {model}":
            yield "E", f"span name should be '{op} {model}'"
        if s["kind"] != "CLIENT":
            yield "E", "kind should be CLIENT"
        if "gen_ai.usage.input_tokens" not in a:
            yield "W", "no token usage; cost can't be computed"
    elif op == "execute_tool":
        tool = a.get("gen_ai.tool.name")
        if not tool:
            yield "E", "no gen_ai.tool.name"
        elif s["name"] != f"execute_tool {tool}":
            yield "E", f"span name should be 'execute_tool {tool}'"
        if "gen_ai.tool.call.id" not in a:
            yield "W", "no gen_ai.tool.call.id"
        if not any(p["attributes"].get("gen_ai.operation.name")
                   == "invoke_agent" for p in ancestors(s, by_id)):
            yield "E", "no invoke_agent span above it"
        if _not_receipt_ready(a):
            yield "W", "consequential, but not receipt-ready"
    if a.get("messaging.operation.type") == "process" \
            and not s["links"] and not s["parent_id"]:
        yield "W", "consumer span not linked to its producer"
    captured = [k for k in CONTENT if k in a]
    if captured:
        yield "W", f"captures content ({len(captured)} opt-in attributes)"


def _not_receipt_ready(a):
    spec = TOOLS.get(a.get("gen_ai.tool.name"))
    return bool(spec and spec.side_effect and not {
        "pronto.tool.target", "pronto.tool.arguments_digest"} <= a.keys())


def lost_context(spans):
    """MCP server spans whose client span is in this file, but is not
    their parent: the traceparent never made it into params._meta."""
    def call(s):
        a = s["attributes"]
        return a.get("mcp.session.id"), a.get("jsonrpc.request.id")
    clients = {call(s): s for s in spans if s["kind"] == "CLIENT"
               and "mcp.method.name" in s["attributes"]}
    for s in spans:
        client = clients.get(call(s))
        if s["kind"] == "SERVER" and client \
                and s["parent_id"] != client["span_id"]:
            yield ("E", s, "lost its caller's context; the client span "
                   f"is in trace {client['trace_id'][:8]}")


def lint(spans):
    by_id = {s["span_id"]: s for s in spans}
    genai = [s for s in spans if {"gen_ai.operation.name",
                                  "messaging.operation.type"}
             & s["attributes"].keys()]
    findings = [(level, s, msg) for s in genai
                for level, msg in check_span(s, by_id)]
    return genai, findings + list(lost_context(genai))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("trace", type=pathlib.Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    genai, findings = lint(otlp.load(args.trace))
    errors = sum(level == "E" for level, _, _ in findings)
    warnings = len(findings) - errors
    failed = errors or (args.strict and warnings)
    print(f"{'FAIL' if failed else 'PASS'} {args.trace.name}: "
          f"{len(genai)} agent spans, {plural(errors, 'error')}, "
          f"{plural(warnings, 'warning')}")
    for level, span, msg in findings:
        name = span["name"].replace("execute_tool ", "tool ")
        print(textwrap.fill(f"{level} {name}: {msg}", width=64,
                            initial_indent="  ",
                            subsequent_indent="      "))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
