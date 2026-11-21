"""Replays a recorded decision from its trace (Chapter 8).

Usage: python -m audit.replay [--all]

Starts from a receipt, as an auditor would: the receipt points at its
trace, the trace's decision links (Chapter 6) name the records the
model saw and their versions, and the snapshot store returns exactly
those versions. The replay reruns Speedy on them, then changes one
input at a time to see which ones change the action.
"""
import argparse
import pathlib
import tempfile

from audit.run import night_receipts
from audit.snapshots import snapshots
from decisions.graph import actions, decision, source
from pronto.model import MockModel
from pronto.speedy import run
from pronto.world import World
from telemetry import otlp
from telemetry.genai import GenAISpans


def inputs(spans, receipt):
    """What the deciding model call saw, by record and version."""
    by_id = {s["span_id"]: s for s in spans}
    span = by_id[receipt["evidence"]["span_id"]]
    _, reads = decision(span, by_id)
    return dict(source(r) for r in reads)


def world_for(seen, snaps, edits=None):
    """A fresh world holding exactly the recorded versions."""
    world = World()
    world.orders, world.photos = {}, {}
    for sid, version in seen.items():
        kind, key = sid.split(":")
        rec = dict(snaps[sid, version])
        if kind == "policy":
            world.policy = rec
        else:
            getattr(world, kind + "s")[key] = rec
    for edit in edits or ():
        edit(world)
    return world


def rerun(seen, snaps, receipt, careless=False, edits=None):
    """Run the turn again. Returns the last consequential outcome."""
    world = world_for(seen, snaps, edits)
    order = next(k for k in world.orders)
    photo = next(iter(world.photos))
    task = {"conversation_id": receipt["evidence"]["conversation_id"],
            "customer_id": world.orders[order]["customer_id"],
            "order_id": order, "photo_id": photo}
    ids = otlp.FixedIds(receipt["evidence"]["trace_id"])
    tracer, exporter = otlp.tracer(ids)
    spans = GenAISpans(tracer, world.clock)
    run(world, MockModel(world.clock, careless), spans, task)
    with tempfile.TemporaryDirectory() as tmp:
        otlp.write(exporter.get_finished_spans(), f"{tmp}/r.json")
        done = actions(otlp.load(f"{tmp}/r.json"))
    return describe(done[-1]["attributes"])


def describe(a):
    """The last consequential call, as tool and status."""
    tool = a["gen_ai.tool.name"]
    if tool == "orders.get":
        return "no action, reply only"
    return f"{tool} {a.get('pronto.effect.status', 'succeeded')}"


def recorded(receipt):
    act, eff = receipt["did_what"]["action"], receipt["did_what"][
        "effect"]
    return f"{act['tool']} {eff['status']}"


def cheaper(world):
    order = next(iter(world.orders.values()))
    order["value_cents"] = 4500


def monday(world):
    world.policy = {**world.policy, "photo_window_hours": 12,
                    "source": {"id": "policy:refunds",
                               "version": "2026-11-16"}}


def replay(spans, receipt, snaps):
    seen = inputs(spans, receipt)
    print(f"receipt {receipt['receipt_id'][:21]}… "
          f"{receipt['issued_at'][11:19]}")
    print(f"recorded       {recorded(receipt)}")
    for sid, version in sorted(seen.items()):
        print(f"  saw {sid} @ {version}")
    same = rerun(seen, snaps, receipt)
    verdict = "reproduced" if same == recorded(receipt) else "diverged"
    print(f"replayed       {same}  ({verdict})")
    sloppy = rerun(seen, snaps, receipt, careless=True)
    verdict = "reproduced" if sloppy == recorded(receipt) else \
        "diverged"
    print(f"no $50 check   {sloppy}  ({verdict})")
    print("what if, with the model that skips the check:")
    for label, edit in (("policy 2026-11-16", monday),
                        ("order worth $45.00", cheaper)):
        out = rerun(seen, snaps, receipt, True, [edit])
        moved = "changes" if out != sloppy else "no change"
        print(f"  {label:<19}{out}  ({moved})")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        recs = night_receipts(pathlib.Path(tmp))
        spans = otlp.load(pathlib.Path(tmp) / "night.json")
    failed = [r for r in recs
              if r["did_what"]["action"]["tool"] == "refunds.create"
              and r["did_what"]["effect"]["status"] == "blocked"]
    print(f"{len(failed)} refunds blocked overnight; replaying "
          f"{'all' if args.all else 'the first'}")
    snaps = snapshots()
    for r in failed if args.all else failed[:1]:
        print()
        replay(spans, r, snaps)


if __name__ == "__main__":
    main()
