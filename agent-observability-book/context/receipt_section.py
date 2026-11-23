"""Part III's receipt sections, built from its labs.

Chapter 8: knowing_what.sources for Speedy's $40 refund. The trace
(Chapter 5) says which records the deciding model call saw and in
which version; the catalog (Chapter 8) adds where each lives, who
vouches for it, how sensitive it is, who wrote it and how far the
agent may rely on it.
"""
import pathlib
from datetime import datetime, timezone

from context.catalog import describe
from decisions.graph import actions, decision, source
from telemetry import otlp

TRACES = pathlib.Path(__file__).parent.parent / "traces"
REFUND_TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
# Chapter 8's rule: Pronto's records decide, customers' are weighed
TRUST = {"pronto": "authoritative", "customer": "evidence"}


def iso(ns):
    t = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def sources(spans, action):
    """knowing_what.sources for one action, from trace + catalog."""
    by_id = {s["span_id"]: s for s in spans}
    found = decision(action, by_id)
    if not found:
        return []
    out = []
    for read in found[1]:
        record, version = source(read)
        entry = describe(record)
        out.append({"id": record, "uri": entry["uri"],
                    "version": version,
                    "retrieved_at": iso(read["end"]),
                    "authority": entry["authority"],
                    "sensitivity": entry["sensitivity"],
                    "origin": entry["origin"],
                    "trust": TRUST.get(entry["origin"], "data")})
    return out


def refund_sources():
    """The three sources behind Saturday's $40 refund."""
    spans = otlp.load(TRACES / "decisions.json")
    refund = next(a for a in actions(spans)
                  if a["trace_id"] == REFUND_TRACE
                  and a["attributes"]["gen_ai.tool.name"]
                  == "refunds.create")
    return sources(spans, refund)
