"""Saturday's conversation across three boundaries (Chapter 4).

Usage: python -m pronto.handoffs OUT_DIR [--drop-context]

Turn 1 replays the $40 refund with Speedy's tools behind Pronto's
MCP server, then queues a confirmation that a worker sends two
minutes later. Turn 2 hands the customer's double-charge complaint
to PayCo's Ledger agent over A2A; Ledger reads the order back
through Pronto's MCP server. Pronto's spans go to Pronto's backend
and PayCo's to PayCo's, as they would in production.
"""
import argparse
import pathlib
from datetime import datetime, timezone

from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter)

from pronto import mcp as wire
from pronto.a2a import LEDGER_CARD, A2AClient, Ledger
from pronto.mcp import RECORD_EVERY_CALL, McpClient, McpServer
from pronto.model import MockModel
from pronto.queue import Queue, deliver
from pronto.run import REFUND_40, TRACE_40
from pronto.speedy import SPEEDY, run
from pronto.world import World
from telemetry import otlp
from telemetry.genai import GenAISpans
from telemetry.waterfall import waterfall

TRACES = {"dispute": "3f1a8c27d94e4b6fa2c0e5b71d8f9a63",
          "notify": "7d2e9c41a0b84f3e9c15d6a8b2f04e17",
          "payco": "c4e81b0f5a2d4e7b9f36a1d0c8b5e294"}
LOST = ["e2c1b5a8f39d4c07a6b2d1e0f4c3b8a9", "91d37c0e5f2a4b68a1e94c7d03b6f215",
        "5a07e3c9b1d84f26b0c51a9e7d3f4862"]
SPANS = ["b7ad6b7169203331", "5fb397be34d26b51", "00f067aa0ba902b6",
         "a1c4e07d9b3f2c58", "1d0f4e2a7c93b815", "6e0c63257de34c92",
         "93564f51e1abe1c2", "c1f4a0d2e8b37a65", "00f067aa0ba902b7",
         "e5b2d8f1c0a94736", "8f2e7d1c4b6a9053", "2c7a9e4f1b8d3065",
         "f40b6c2e9d1a8537", "7b3e1a9c5f2d0846"]
DISPUTE = {"conversation_id": "conv_44be2d", "customer_id": "cust_7f3a91",
           "order_id": "ord_5521", "intent": "dispute",
           "message": "Also, my card was charged twice for this order."}


def service(name, ids, backend, cloud=("aws", "us-west-2"),
            sampler=None):
    resource = {"service.name": name, "deployment.environment.name":
                "production", "cloud.provider": cloud[0],
                "cloud.region": cloud[1]}
    tracer, _ = otlp.tracer(ids, resource, (name, "1.0"), backend,
                            sampler)
    return tracer


def at(hour, minute, second):
    return datetime(2026, 11, 14, hour, minute, second,
                    tzinfo=timezone.utc)


def conversation():
    """Run both turns. Returns (pronto spans, payco spans, replies)."""
    world, pronto, payco = World(), InMemorySpanExporter(), \
        InMemorySpanExporter()
    speedy, _ = otlp.tracer(otlp.FixedIds(
        [TRACE_40, TRACES["dispute"]], SPANS), exporter=pronto)
    # The server starts traces of its own only if context is lost
    server = McpServer(world, service("pronto-commerce-mcp", otlp.FixedIds(
        LOST, seed=11), pronto, sampler=RECORD_EVERY_CALL),
        ["orders.get", "refunds.create"])
    queue = Queue(world, speedy)
    mcp = McpClient(world, speedy, server, "mcps_19c4850a", SPEEDY)
    world.routes = {"orders.get": lambda a: mcp.call("orders.get", a),
                    "refunds.create":
                        lambda a: mcp.call("refunds.create", a),
                    "notify.queue": queue.send}
    spans = GenAISpans(speedy, world.clock)
    replies = [run(world, MockModel(world.clock), spans,
                   {**REFUND_40, "notify": True})]

    ledger_tracer = service("payco-ledger", otlp.FixedIds(
        TRACES["payco"], seed=13), payco, ("gcp", "us-central1"))
    ledger = Ledger(world, ledger_tracer, McpClient(
        world, ledger_tracer, server, "mcps_7f20b1e9", LEDGER_CARD))
    a2a = A2AClient(world, speedy, ledger, LEDGER_CARD)

    def open_dispute(args):
        task = a2a.send("Open a dispute for a duplicate card charge.",
                        args, DISPUTE["conversation_id"])
        dispute = task["artifacts"][0]["parts"][0]["data"]["dispute"]
        return {"ref": f"dispute:{dispute}", "status": "succeeded"}

    world.routes["disputes.open"] = open_dispute
    world.clock.set(at(2, 7, 50))                # the customer replies
    replies.append(run(world, MockModel(world.clock,
                                        call_ids=["call_a301"]),
                       spans, DISPUTE))

    world.clock.set(at(2, 9, 20))                # the worker wakes up
    deliver(world, service("pronto-notifier", otlp.FixedIds(
        TRACES["notify"], seed=17), pronto), queue)
    return pronto.get_finished_spans(), payco.get_finished_spans(), \
        replies


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--drop-context", action="store_true",
                        help="the lab's broken run: MCP calls carry no "
                        "traceparent in _meta")
    args = parser.parse_args(argv)
    if args.drop_context:
        wire.inject = lambda carrier: carrier
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    pronto_spans, payco_spans, replies = conversation()
    otlp.write(pronto_spans, out / "handoff-pronto.json")
    otlp.write(payco_spans, out / "handoff-payco.json")
    print("Pronto's backend")
    print(waterfall(otlp.load(out / "handoff-pronto.json")))
    print("\nPayCo's backend")
    print(waterfall(otlp.load(out / "handoff-payco.json")))
    print(f"\nSpeedy: {replies[0]}\nSpeedy: {replies[1]}")


if __name__ == "__main__":
    main()
