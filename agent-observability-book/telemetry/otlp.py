"""Tracer setup and OTLP JSON files (Chapter 4).

Traces are written in OTLP JSON, the format the OpenTelemetry
Collector's file exporter writes, so any trace in this repo can be
loaded into a backend, and any backend's export can be checked with
telemetry.lint.
"""
import json
import pathlib
import random

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter)
from opentelemetry.sdk.trace.id_generator import IdGenerator

RUNTIME = {"service.name": "pronto-support-runtime",
           "service.version": "2.3.1",
           "deployment.environment.name": "production",
           "cloud.provider": "aws", "cloud.region": "us-west-2"}
KINDS = {0: "UNSPECIFIED", 1: "INTERNAL", 2: "SERVER", 3: "CLIENT",
         4: "PRODUCER", 5: "CONSUMER"}


class FixedIds(IdGenerator):
    """Repeatable IDs, so the book's trace matches its receipts."""

    def __init__(self, trace_ids, span_ids=(), seed=7):
        if isinstance(trace_ids, str):
            trace_ids = [trace_ids]
        self.trace_ids, self.span_ids = list(trace_ids), list(span_ids)
        self.rng = random.Random(seed)

    def generate_trace_id(self):
        if len(self.trace_ids) > 1:
            return int(self.trace_ids.pop(0), 16)
        return int(self.trace_ids[0], 16)

    def generate_span_id(self):
        if self.span_ids:
            return int(self.span_ids.pop(0), 16)
        return self.rng.getrandbits(64)


def tracer(ids, resource=RUNTIME, scope=("pronto.speedy", "2.3.1"),
           exporter=None, sampler=None):
    """A tracer that keeps finished spans in memory. Pass the same
    exporter to several tracers to model one backend."""
    exporter = exporter or InMemorySpanExporter()
    provider = TracerProvider(resource=Resource(resource),
                              id_generator=ids, sampler=sampler)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer(*scope), exporter


def _value(v):
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, (list, tuple)):
        return {"arrayValue": {"values": [_value(x) for x in v]}}
    return {"stringValue": str(v)}


def _attrs(attributes):
    return [{"key": k, "value": _value(v)} for k, v in attributes.items()]


def _span(s):
    return {
        "traceId": f"{s.context.trace_id:032x}",
        "spanId": f"{s.context.span_id:016x}",
        "parentSpanId": f"{s.parent.span_id:016x}" if s.parent else "",
        "name": s.name,
        "kind": s.kind.value + 1,           # SDK 0-based, OTLP 1-based
        "startTimeUnixNano": str(s.start_time),
        "endTimeUnixNano": str(s.end_time),
        "attributes": _attrs(s.attributes),
        "links": [{"traceId": f"{link.context.trace_id:032x}",
                   "spanId": f"{link.context.span_id:016x}",
                   "attributes": _attrs(link.attributes or {})}
                  for link in s.links],
        "status": {"code": s.status.status_code.value,
                   "message": s.status.description or ""}}


def to_otlp(spans):
    """Finished SDK spans as one OTLP JSON export request, grouped by
    service (resource) the way a Collector would forward them."""
    groups = {}
    for s in sorted(spans, key=lambda s: s.start_time):
        key = tuple(sorted(s.resource.attributes.items()))
        groups.setdefault(key, (s, []))[1].append(s)
    return {"resourceSpans": [{
        "resource": {"attributes": _attrs(first.resource.attributes)},
        "scopeSpans": [{
            "scope": {"name": first.instrumentation_scope.name,
                      "version": first.instrumentation_scope.version},
            "spans": [_span(s) for s in members]}]}
        for first, members in groups.values()]}


def write(spans, path):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_otlp(spans)) + "\n", encoding="utf-8")


def _plain(value):
    (kind, v), = value.items()
    if kind == "arrayValue":
        return [_plain(x) for x in v.get("values", [])]
    return int(v) if kind == "intValue" else v


def load(path):
    """Read OTLP JSON lines (ours, or a Collector file export) into
    plain dicts, one per span, sorted by start time."""
    spans = []
    for line in pathlib.Path(path).read_text().splitlines():
        if not line.strip():
            continue
        for rs in json.loads(line).get("resourceSpans", []):
            resource = {a["key"]: _plain(a["value"])
                        for a in rs.get("resource", {}).get("attributes", [])}
            for ss in rs.get("scopeSpans", []):
                for s in ss.get("spans", []):
                    spans.append({
                        "trace_id": s["traceId"], "span_id": s["spanId"],
                        "parent_id": s.get("parentSpanId") or None,
                        "name": s["name"],
                        "kind": KINDS.get(int(s.get("kind", 0)), "?"),
                        "start": int(s["startTimeUnixNano"]),
                        "end": int(s["endTimeUnixNano"]),
                        "status": int(s.get("status", {}).get("code", 0)),
                        "attributes": {a["key"]: _plain(a["value"])
                                       for a in s.get("attributes", [])},
                        "links": [{"trace_id": link["traceId"],
                                   "span_id": link["spanId"],
                                   "attributes": {
                                       a["key"]: _plain(a["value"])
                                       for a in link.get("attributes",
                                                         [])}}
                                  for link in s.get("links", [])],
                        "resource": resource})
    return sorted(spans, key=lambda s: s["start"])


KIND_NUMBERS = {name: number for number, name in KINDS.items()}


def write_plain(spans, path):
    """Write spans in load()'s plain shape back out as OTLP JSON, so a
    pipeline stage's output reads like any other export (Chapter 7)."""
    groups = {}
    for s in spans:
        key = json.dumps(s["resource"], sort_keys=True)
        groups.setdefault(key, (s["resource"], []))[1].append(s)
    doc = {"resourceSpans": [{
        "resource": {"attributes": _attrs(resource)},
        "scopeSpans": [{"scope": {"name": "pronto"}, "spans": [{
            "traceId": s["trace_id"], "spanId": s["span_id"],
            "parentSpanId": s["parent_id"] or "", "name": s["name"],
            "kind": KIND_NUMBERS.get(s["kind"], 0),
            "startTimeUnixNano": str(s["start"]),
            "endTimeUnixNano": str(s["end"]),
            "attributes": _attrs(s["attributes"]),
            "links": [{"traceId": link["trace_id"],
                       "spanId": link["span_id"],
                       "attributes": _attrs(link.get("attributes", {}))}
                      for link in s["links"]],
            "status": {"code": s["status"]}} for s in members]}]}
        for resource, members in groups.values()]}
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc) + "\n"
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))
