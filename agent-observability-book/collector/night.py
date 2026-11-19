"""A night of Speedy's traffic, for the Collector lab (Chapter 7).

Usage: python -m collector.night OUT.json [--conversations 1000]

Saturday, midnight to 6 a.m. Most customers ask where an order is;
some report spoiled food. A few things go wrong the way they do in
production: the orders service times out, a model skips the $50
check, a model call runs slow, and a customer types an email address
where the order number should go. From 1 a.m. to 3 a.m., content
capture was left on, so prompts and tool results are in the spans,
with the customers' names, emails and phone numbers in them.

Every customer is fictional. Their names, emails and phone numbers
are canaries: the lab scans each stage's output for them.
"""
import argparse
import os
import random
from datetime import datetime, timedelta, timezone

from pronto.model import MockModel
from pronto.speedy import run
from pronto.tools import Unavailable
from pronto.world import World
from telemetry import otlp
from telemetry.genai import CAPTURE, GenAISpans

FIRST = ["Maria", "James", "Aiko", "Priya", "Omar", "Lena", "Diego",
         "Grace", "Tomas", "Nadia", "Kwame", "Sofia", "Ravi", "Elena"]
LAST = ["Lopez", "Okafor", "Tanaka", "Sharma", "Haddad", "Novak",
        "Reyes", "Chen", "Silva", "Petrov", "Mensah", "Rossi"]
ITEMS = [("strawberries, 2 lb", 800), ("salmon fillets", 2400),
         ("chicken thighs", 1500), ("eggs, 18 count", 700),
         ("spinach, 1 lb", 500), ("ribeye steaks", 4600),
         ("party platter", 7900), ("yogurt, 6 pack", 650)]
START = datetime(2026, 11, 14, 0, 0, 0, tzinfo=timezone.utc)
SLOW_S = 45.0                       # one model call that hangs


class SlowModel(MockModel):
    """A model whose second call in the turn hangs (Chapter 7)."""

    def complete(self, messages):
        if self.clock and self.turn == 1:
            self.clock.advance(SLOW_S)
        return super().complete(messages)


def customers(rng, n):
    people = []
    for i in range(n):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        people.append({
            "id": f"cust_{rng.getrandbits(24):06x}",
            "name": f"{first} {last}",
            "email": f"{first}.{last}{i}@example.com".lower(),
            "phone": f"415-555-{rng.randrange(100, 200):04d}"})
    return people


def conversations(n=1000, seed=2026):
    """The night's plan: one task per conversation, plus its faults."""
    rng = random.Random(seed)
    plan = []
    for i, person in enumerate(customers(rng, n)):
        item, cents = rng.choice(ITEMS)
        cents = int(cents * rng.uniform(0.6, 1.4)) // 10 * 10
        oid, pid = f"ord_{7000 + i}", f"photo_{9000 + i}"
        refund = rng.random() < 0.3
        task = {"conversation_id": f"conv_{rng.getrandbits(24):06x}",
                "customer_id": person["id"], "order_id": oid}
        if refund:
            task.update(photo_id=pid, message=(
                f"{person['name']} here, {person['phone']}. My {item}"
                " arrived spoiled. Photo attached."))
        else:
            task.update(intent="status", message=(
                f"Hi, this is {person['name']} ({person['email']}). "
                f"Where is order {oid}?"))
            if rng.random() < 0.02:          # wrong field, real data
                task["order_id"] = person["email"]
        plan.append({
            "task": task, "person": person, "item": item, "order": oid,
            "cents": cents, "refund": refund,
            "hours": rng.randrange(1, 41),
            "status": rng.choice(["delivered", "out for delivery",
                                  "packed"]),
            "at": START + timedelta(seconds=21.6 * i),
            "timeout": rng.random() < 0.015,
            "careless": refund and rng.random() < 0.08,
            "slow": rng.random() < 0.02})
    return plan


def stock(world, c):
    """Put the conversation's order and photo into the world."""
    p, oid = c["person"], c["order"]
    world.orders[oid] = {
        "customer_id": p["id"], "status": c["status"], "item": c["item"],
        "perishable": True, "value_cents": c["cents"],
        "deliver_to": {"name": p["name"], "phone": p["phone"],
                       "email": p["email"]},
        "source": {"id": f"order:{oid}", "version": "etag-0001"}}
    if c["refund"]:
        pid = c["task"]["photo_id"]
        world.photos[pid] = {
            "order_id": oid, "shows_spoilage": True,
            "hours_after_delivery": c["hours"],
            "source": {"id": f"photo:{pid}", "version": "etag-0001"}}


def timed_out(args):
    raise Unavailable("orders service timed out")


def night(n=1000, seed=2026):
    """Run the night. Returns (spans, plan)."""
    plan = conversations(n, seed)
    rng = random.Random(seed + 1)
    ids = otlp.FixedIds([f"{rng.getrandbits(128):032x}"
                         for _ in range(n + 1)], seed=seed)
    tracer, exporter = otlp.tracer(ids)
    world = World()
    spans = GenAISpans(tracer, world.clock, decisions=True)
    saved = os.environ.get(CAPTURE)
    try:
        for c in plan:
            world.clock.set(c["at"])
            stock(world, c)
            world.routes = {"orders.get": timed_out} if c["timeout"] \
                else {}
            hour = c["at"].hour
            os.environ[CAPTURE] = "true" if 1 <= hour < 3 else "false"
            kind = SlowModel if c["slow"] else MockModel
            run(world, kind(world.clock, c["careless"]), spans,
                c["task"])
    finally:
        os.environ.pop(CAPTURE, None)
        if saved is not None:
            os.environ[CAPTURE] = saved
    return exporter.get_finished_spans(), plan


def canaries(plan):
    """Every fictional name, email and phone number in the night."""
    return sorted({c["person"][k] for c in plan
                   for k in ("name", "email", "phone")})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out")
    parser.add_argument("--conversations", type=int, default=1000)
    args = parser.parse_args(argv)
    spans, plan = night(args.conversations)
    otlp.write(spans, args.out)
    print(f"wrote {args.out}: {len(plan)} conversations, "
          f"{len(spans)} spans")


if __name__ == "__main__":
    main()
