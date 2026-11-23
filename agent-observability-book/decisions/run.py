"""Three of Speedy's turns, traced with decision links (Chapter 5).

Usage: python -m decisions.run OUT_DIR

Saturday 2:06 a.m.: the $40 strawberry refund, with the same trace
and span IDs as Chapter 2's receipt. Saturday 2:19 a.m.: $62 of
spoiled chicken, which Speedy hands to a person under the $50 rule.
Monday 10:14 a.m.: $18 of cracked eggs, refunded under the refund
policy finance published that morning. All three run in one World,
so refund and case numbers carry on from one turn to the next.
"""
import argparse
import pathlib
from datetime import datetime, timezone

from pronto.model import MockModel
from pronto.run import REFUND_40, SPANS_40, TRACE_40
from pronto.speedy import run
from pronto.world import MONDAY_POLICY, World
from telemetry import otlp
from telemetry.genai import GenAISpans

CHICKEN_62 = {"conversation_id": "conv_58d1f7",
              "customer_id": "cust_4b7d10", "order_id": "ord_5534",
              "photo_id": "photo_7e9",
              "message": "The chicken was warm and smelled bad."}
EGGS_18 = {"conversation_id": "conv_6e04b2",
           "customer_id": "cust_91d2e0", "order_id": "ord_5602",
           "photo_id": "photo_8a2",
           "message": "Half the eggs arrived cracked. Photo attached."}
TRACES = [TRACE_40, "a3c1e5d7f9b24680ace13579bdf02468",
          "d81f3b6c2e9a47058f1c6b3e0a7d5924"]


def at(day, hour, minute, second):
    return datetime(2026, 11, day, hour, minute, second,
                    tzinfo=timezone.utc)


def turns():
    """Run the three turns. Returns (spans, replies)."""
    world = World()
    tracer, exporter = otlp.tracer(otlp.FixedIds(TRACES, SPANS_40))
    spans = GenAISpans(tracer, world.clock, decisions=True)
    replies = []
    for when, task, policy in [(at(14, 2, 6, 37), REFUND_40, None),
                               (at(14, 2, 19, 44), CHICKEN_62, None),
                               (at(16, 10, 14, 3), EGGS_18,
                                MONDAY_POLICY)]:
        world.clock.set(when)
        if policy:
            world.policy.update(policy)
        replies.append(run(world, MockModel(world.clock), spans, task))
    return exporter.get_finished_spans(), replies


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    args = parser.parse_args(argv)
    spans, replies = turns()
    otlp.write(spans, args.out / "decisions.json")
    print(f"wrote {args.out / 'decisions.json'}: {len(spans)} spans "
          f"in {len(replies)} traces")
    for reply in replies:
        print(f"Speedy: {reply}")


if __name__ == "__main__":
    main()
