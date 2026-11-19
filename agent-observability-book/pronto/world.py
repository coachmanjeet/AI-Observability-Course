"""Pronto's systems of record for one run (Chapter 4).

Book 1's World, extended for Book 2: orders and photos live here too,
refund IDs come from a sequence so the book's outputs are repeatable,
and a simulated clock stamps every span.
"""
import sqlite3
from datetime import datetime, timezone

DEFAULT_POLICY = {"approval_above_cents": 5000,     # the $50 rule
                  "photo_window_hours": 24,          # perishables
                  "return_window_days": 30,          # non-perishables
                  "source": {"id": "policy:refunds",  # Chapter 6
                             "version": "2026-10-01"}}
# Monday, Nov 16: finance shortens the photo window after Saturday
MONDAY_POLICY = {"photo_window_hours": 12,
                 "source": {"id": "policy:refunds",
                            "version": "2026-11-16"}}

# The version each record had when Speedy read it (an ETag)
ETAGS = {"ord_5521": "etag-9f2c", "ord_5530": "etag-a7e3",
         "ord_5534": "etag-b04d", "ord_5602": "etag-c210",
         "photo_7c1": "etag-41c7", "photo_7d4": "etag-52d0",
         "photo_7e9": "etag-5e88", "photo_8a2": "etag-6b19"}

# 2026-11-14 02:06:37 UTC: the start of Saturday's 2:07 a.m. refund
INCIDENT_START = datetime(2026, 11, 14, 2, 6, 37, tzinfo=timezone.utc)


class Clock:
    """Simulated time, so every trace in the book is reproducible."""

    def __init__(self, start=INCIDENT_START):
        self.ns = int(start.timestamp()) * 1_000_000_000

    def now(self):
        return self.ns

    def advance(self, seconds):
        self.ns += round(seconds * 1_000_000_000)

    def set(self, when):
        """Jump forward to a wall-clock time (never backward)."""
        self.ns = max(self.ns, int(when.timestamp()) * 1_000_000_000)


class World:
    def __init__(self, policy=None, refund_seq=9931):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE refunds (refund_id TEXT PRIMARY KEY,"
                        " order_id TEXT UNIQUE, cents INTEGER)")
        self.db.execute("CREATE TABLE cases (case_id TEXT PRIMARY KEY,"
                        " order_id TEXT, reason TEXT)")
        self.policy = {**DEFAULT_POLICY, **(policy or {})}
        self.refund_seq = refund_seq
        self.clock = Clock()
        self.routes = {}             # tool name -> remote call (Ch 5)
        self.orders = {
            "ord_5521": {"customer_id": "cust_7f3a91", "status": "delivered",
                         "item": "strawberries, 2 lb", "perishable": True,
                         "value_cents": 4000},
            "ord_5530": {"customer_id": "cust_2c88e4", "status": "delivered",
                         "item": "salmon fillets, 4 pack", "perishable": True,
                         "value_cents": 8500},
            "ord_5534": {"customer_id": "cust_4b7d10", "status": "delivered",
                         "item": "chicken thighs, family pack",
                         "perishable": True, "value_cents": 6200},
            "ord_5602": {"customer_id": "cust_91d2e0", "status": "delivered",
                         "item": "eggs, 18 count", "perishable": True,
                         "value_cents": 1800},
        }
        self.photos = {
            "photo_7c1": {"order_id": "ord_5521", "shows_spoilage": True,
                          "hours_after_delivery": 3},
            "photo_7d4": {"order_id": "ord_5530", "shows_spoilage": True,
                          "hours_after_delivery": 5},
            "photo_7e9": {"order_id": "ord_5534", "shows_spoilage": True,
                          "hours_after_delivery": 2},
            "photo_8a2": {"order_id": "ord_5602", "shows_spoilage": True,
                          "hours_after_delivery": 6},
        }
        # Chapter 6: every record says which version of itself it is
        for kind, records in (("order", self.orders),
                              ("photo", self.photos)):
            for key, record in records.items():
                record["source"] = {"id": f"{kind}:{key}",
                                    "version": ETAGS[key]}
