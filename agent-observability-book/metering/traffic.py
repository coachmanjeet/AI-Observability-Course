"""A month of Speedy's conversations for one tenant (Part VII).

Speedy runs its real loop with the mock model, in one World per
tenant, under the refund policy finance published on Nov 16,
2026. Each agent span carries the tenant (pronto.tenant.id), the
way a multi-tenant runtime stamps every turn it serves. Some
customers come back about the same order within a week. Those
follow-ups are real conversations too, and they decide whether
the first one resolved.

Usage: python -m metering.traffic TENANT OUT.json
       [--start 2027-02-01] [--days 28] [--timeouts 0.015]
"""

import argparse
import random
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from collector.night import ITEMS, timed_out
from pronto.model import MockModel
from pronto.speedy import run
from pronto.world import MONDAY_POLICY, World
from telemetry import otlp
from telemetry.genai import GenAISpans

TENANT = "pronto.tenant.id"
# Conversations a day, and the share that report spoiled food
TENANTS = {
    "tenant:pronto": {
        "name": "Pronto",
        "per_day": 100,
        "refunds": 0.30,
    },
    "tenant:hilltop": {
        "name": "Hilltop Market",
        "per_day": 40,
        "refunds": 0.25,
    },
    "tenant:corner": {
        "name": "Corner Basket",
        "per_day": 15,
        "refunds": 0.35,
    },
    "tenant:bayside": {
        "name": "Bayside Foods",
        "per_day": 70,
        "refunds": 0.20,
    },
}
# How often a customer comes back about the same order, by what
# happened the first time
COME_BACK = {
    "timeout": 0.80,
    "declined": 0.45,
    "status": 0.04,
    "refund": 0.02,
    "escalated": 0.0,
}


class TenantSpans(GenAISpans):
    """GenAISpans that stamp the tenant on every agent span."""

    def __init__(self, tracer, clock, tenant):
        super().__init__(tracer, clock, decisions=True)
        self.tenant = tenant

    @contextmanager
    def agent(self, agent, conversation_id):
        with super().agent(agent, conversation_id) as span:
            span.set_attribute(TENANT, self.tenant)
            yield span


def conv_id(rng):
    return f"conv_{rng.getrandbits(32):08x}"


def first_time(c, window_h, approval_cents):
    """What happens in a conversation, decided by the plan."""
    if c["timeout"]:
        return "timeout"
    if not c["refund"]:
        return "status"
    if c["hours"] > window_h:
        return "declined"
    return (
        "escalated" if c["cents"] > approval_cents else "refund"
    )


def plan(
    tenant, start, days, timeouts=0.015, seed=2027, per_day=None
):
    """Every conversation in the month, in time order."""
    profile = TENANTS[tenant]
    rng = random.Random(f"{tenant}:{start:%Y-%m-%d}:{seed}")
    n = (per_day or profile["per_day"]) * days
    window = MONDAY_POLICY["photo_window_hours"]
    convs = []
    for _ in range(n):
        item, cents = rng.choice(ITEMS)
        refund = rng.random() < profile["refunds"]
        c = {
            "tenant": tenant,
            "item": item,
            "cents": int(cents * rng.uniform(0.6, 1.4))
            // 10
            * 10,
            "conversation_id": conv_id(rng),
            "customer_id": f"cust_{rng.getrandbits(24):06x}",
            "order_id": f"ord_{rng.getrandbits(32):08x}",
            "refund": refund,
            "follow_up": False,
            "hours": rng.choice(
                [1, 2, 3, 4, 5, 6, 8, 10, 11, 20]
            ),
            "status": rng.choice(
                ["delivered", "out for delivery"]
            ),
            "at": start
            + timedelta(seconds=rng.uniform(0, days * 86400)),
            "timeout": rng.random() < timeouts,
        }
        convs.append(c)
        what = first_time(c, window, 5000)
        if rng.random() < COME_BACK[what]:
            back = dict(
                c,
                refund=False,
                follow_up=True,
                timeout=rng.random() < timeouts,
                conversation_id=conv_id(rng),
                at=c["at"]
                + timedelta(hours=rng.uniform(2, 6 * 24)),
            )
            convs.append(back)
    return sorted(convs, key=lambda c: c["at"])


def stock(world, c):
    world.orders[c["order_id"]] = {
        "customer_id": c["customer_id"],
        "status": c["status"],
        "item": c["item"],
        "perishable": True,
        "value_cents": c["cents"],
        "source": {
            "id": f"order:{c['order_id']}",
            "version": "etag-0001",
        },
    }
    if c["refund"]:
        pid = "photo_" + c["order_id"][4:]
        world.photos[pid] = {
            "order_id": c["order_id"],
            "shows_spoilage": True,
            "hours_after_delivery": c["hours"],
            "source": {
                "id": f"photo:{pid}",
                "version": "etag-0001",
            },
        }
        return pid
    return None


def task(c, photo_id):
    t = {
        "conversation_id": c["conversation_id"],
        "customer_id": c["customer_id"],
        "order_id": c["order_id"],
    }
    if photo_id:
        t.update(
            photo_id=photo_id,
            message=f"My {c['item']} arrived spoiled. Photo.",
        )
    else:
        t.update(intent="status", message="Where is my order?")
    return t


def month(
    tenant, start, days, timeouts=0.015, seed=2027, per_day=None
):
    """Run the month. Returns (finished spans, plan)."""
    convs = plan(tenant, start, days, timeouts, seed, per_day)
    rng = random.Random(f"{tenant}:ids:{seed}")
    ids = otlp.FixedIds(
        [
            f"{rng.getrandbits(128):032x}"
            for _ in range(len(convs) + 1)
        ],
        seed=seed,
    )
    tracer, exporter = otlp.tracer(ids)
    world = World(policy=MONDAY_POLICY)
    spans = TenantSpans(tracer, world.clock, tenant)
    for c in convs:
        world.clock.set(c["at"])
        photo = stock(world, c)
        world.routes = (
            {"orders.get": timed_out} if c["timeout"] else {}
        )
        run(
            world, MockModel(world.clock), spans, task(c, photo)
        )
    return exporter.get_finished_spans(), convs


def day(text):
    return datetime.fromisoformat(text).replace(
        tzinfo=timezone.utc
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0]
    )
    parser.add_argument("tenant", choices=sorted(TENANTS))
    parser.add_argument("out")
    parser.add_argument(
        "--start", type=day, default=day("2027-02-01")
    )
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--timeouts", type=float, default=0.015)
    args = parser.parse_args(argv)
    spans, convs = month(
        args.tenant, args.start, args.days, args.timeouts
    )
    otlp.write(spans, args.out)
    print(
        f"wrote {args.out}: {len(convs)} conversations, "
        f"{len(spans)} spans"
    )


if __name__ == "__main__":
    main()
