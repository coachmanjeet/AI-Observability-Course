"""Runs one Speedy turn and writes its trace (Chapter 4).

Usage: python -m pronto.run [--order ord_5530] [--careless] OUT.json

Without flags it replays Saturday's 2:07 a.m. refund: $40 of spoiled
strawberries, photo attached. --order ord_5530 asks for Night Owl's
$85 salmon refund instead; --careless makes the model skip the $50
check, so the refund tool's own rule has to stop it.
"""
import argparse

from pronto.model import MockModel
from pronto.speedy import run
from pronto.world import World
from telemetry import otlp
from telemetry.genai import GenAISpans
from telemetry.waterfall import waterfall

REFUND_40 = {"conversation_id": "conv_44be2d", "customer_id": "cust_7f3a91",
             "order_id": "ord_5521", "photo_id": "photo_7c1",
             "message": "My strawberries arrived moldy. Photo attached."}
REFUND_85 = {"conversation_id": "conv_51a0c3", "customer_id": "cust_2c88e4",
             "order_id": "ord_5530", "photo_id": "photo_7d4",
             "message": "The salmon smelled off. Photo attached."}
# The W3C trace-context example IDs, which Chapter 2's receipts carry
TRACE_40 = "4bf92f3577b34da6a3ce929d0e0e4736"
SPANS_40 = ["b7ad6b7169203331", "5fb397be34d26b51", "00f067aa0ba902b6",
            "1d0f4e2a7c93b815", "6e0c63257de34c92", "93564f51e1abe1c2",
            "c1f4a0d2e8b37a65", "00f067aa0ba902b7", "8f2e7d1c4b6a9053"]


def trace_turn(task, careless=False, trace_id=TRACE_40, span_ids=()):
    world = World()
    tracer, exporter = otlp.tracer(otlp.FixedIds(trace_id, span_ids))
    spans = GenAISpans(tracer, world.clock)
    reply = run(world, MockModel(world.clock, careless), spans, task)
    return reply, exporter.get_finished_spans()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out")
    parser.add_argument("--order", default="ord_5521")
    parser.add_argument("--careless", action="store_true")
    args = parser.parse_args(argv)
    if args.order == "ord_5521":
        reply, spans = trace_turn(REFUND_40, args.careless,
                                  span_ids=SPANS_40)
    else:
        reply, spans = trace_turn(REFUND_85, args.careless,
                                  trace_id="0af7651916cd43dd8448eb211c80319c")
    otlp.write(spans, args.out)
    print(waterfall(otlp.load(args.out)))
    print(f"\nSpeedy: {reply}")


if __name__ == "__main__":
    main()
