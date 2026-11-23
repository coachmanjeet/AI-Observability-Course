"""Speedy on a real model, traced into a real backend (Chapter 4).

Usage:
  export PRONTO_MODEL_BASE_URL=https://api.openai.com/v1
  export PRONTO_MODEL_API_KEY=...
  export PRONTO_MODEL=gpt-4.1-mini
  python -m pronto.live OUT.json [--otlp http://localhost:4318]

Optional. Every other lab, and every output printed in the book,
runs on MockModel, so the book stays reproducible. This path swaps
in any model behind an OpenAI-compatible chat completions endpoint
(OpenAI, Azure OpenAI, vLLM, Ollama, LiteLLM and others), runs
Saturday's $40 refund through the same loop, tools and
instrumentation, writes the trace, and lints it. With --otlp it
also posts the trace as OTLP/HTTP JSON to a receiver such as
Jaeger or an OpenTelemetry Collector, so you can see the same spans
in a real tool. A real model may decide differently from the mock;
the lint and the receipts show you exactly how.
"""
import argparse
import json
import os
import pathlib
import time
import urllib.request

from pronto.model import SYSTEM, Reply, ToolCall
from pronto.run import REFUND_40
from pronto.speedy import run
from pronto.world import World
from telemetry import otlp
from telemetry.genai import GenAISpans
from telemetry.waterfall import waterfall

# OpenAI-style names can't contain dots, so tools travel as
# orders_get and come back as orders.get.
TOOLS = {
    "policy.lookup": ("Read Pronto's current refund policy.", {}),
    "orders.get": ("Read one order.",
                   {"order_id": {"type": "string"}}),
    "photos.verify": ("Check a customer's photo of an item.",
                      {"photo_id": {"type": "string"}}),
    "refunds.create": ("Refund an order. Over $50 needs a person.",
                       {"order_id": {"type": "string"},
                        "amount": {"type": "string",
                                   "description": "dollars, as 40.00"},
                        "currency": {"type": "string"}}),
    "cases.escalate": ("Hand the case to a person.",
                       {"order_id": {"type": "string"},
                        "reason": {"type": "string"}}),
}


def wire_name(name):
    return name.replace(".", "_")


def tool_specs():
    return [{"type": "function", "function": {
        "name": wire_name(name), "description": desc,
        "parameters": {"type": "object", "properties": props,
                       "required": list(props)}}}
        for name, (desc, props) in TOOLS.items()]


def to_wire(messages):
    """The loop's messages as chat-completions messages."""
    out = [{"role": "system", "content": SYSTEM}]
    pending = []
    for m in messages:
        if m["role"] == "user":
            t = m["task"]
            out.append({"role": "user", "content": (
                f"{t['message']}\n\norder_id: {t['order_id']}\n"
                f"photo_id: {t['photo_id']}\n"
                f"customer_id: {t['customer_id']}")})
        elif m["role"] == "assistant":
            r = m["reply"]
            msg = {"role": "assistant", "content": r.text or None}
            if r.tool_calls:
                msg["tool_calls"] = [{
                    "id": c.id, "type": "function", "function": {
                        "name": wire_name(c.name),
                        "arguments": json.dumps(c.arguments)}}
                    for c in r.tool_calls]
            out.append(msg)
            pending = [c.id for c in r.tool_calls]
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": pending.pop(0),
                        "content": json.dumps(m["result"])})
    return out


class LiveModel:
    """MockModel's interface over an OpenAI-compatible endpoint."""
    provider = "openai"

    def __init__(self, base_url, api_key, model, clock=None,
                 timeout=60):
        self.base_url = base_url.rstrip("/")
        self.api_key, self.name = api_key, model
        self.clock, self.timeout = clock, timeout
        self.names = {wire_name(n): n for n in TOOLS}

    def complete(self, messages):
        body = {"model": self.name, "messages": to_wire(messages),
                "tools": tool_specs(), "temperature": 0}
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        seconds = time.monotonic() - start
        choice = data["choices"][0]
        msg, usage = choice["message"], data.get("usage", {})
        calls = [ToolCall(c["id"], self.names[c["function"]["name"]],
                          json.loads(c["function"]["arguments"] or "{}"))
                 for c in msg.get("tool_calls") or []]
        cached = (usage.get("prompt_tokens_details") or {}).get(
            "cached_tokens", 0)
        reply = Reply(id=data.get("id", ""),
                      model=data.get("model", self.name),
                      text=msg.get("content") or "", tool_calls=calls,
                      finish_reason=choice.get("finish_reason", "stop"),
                      input_tokens=usage.get("prompt_tokens", 0),
                      output_tokens=usage.get("completion_tokens", 0),
                      cache_read_tokens=cached, seconds=seconds,
                      messages=list(messages), system=SYSTEM)
        if self.clock:
            self.clock.advance(seconds)
        return reply


def export(path, endpoint, timeout=10):
    """POST the trace file to an OTLP/HTTP receiver, as JSON."""
    req = urllib.request.Request(
        f"{endpoint.rstrip('/')}/v1/traces",
        data=pathlib.Path(path).read_bytes(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


def trace_live(model, task=REFUND_40):
    world = World()
    tracer, exporter = otlp.tracer(None)
    spans = GenAISpans(tracer, world.clock)
    model.clock = world.clock
    reply = run(world, model, spans, task)
    return reply, exporter.get_finished_spans()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out")
    parser.add_argument("--otlp", help="OTLP/HTTP endpoint, e.g. "
                        "http://localhost:4318")
    args = parser.parse_args(argv)
    env = os.environ
    missing = [k for k in ("PRONTO_MODEL_BASE_URL", "PRONTO_MODEL")
               if not env.get(k)]
    if missing:
        parser.exit(2, f"set {', '.join(missing)} first\n")
    model = LiveModel(env["PRONTO_MODEL_BASE_URL"],
                      env.get("PRONTO_MODEL_API_KEY", ""),
                      env["PRONTO_MODEL"])
    reply, spans = trace_live(model)
    otlp.write(spans, args.out)
    print(waterfall(otlp.load(args.out)))
    print(f"\nSpeedy: {reply}")
    if args.otlp:
        status = export(args.out, args.otlp)
        print(f"exported to {args.otlp}: HTTP {status}")


if __name__ == "__main__":
    main()
