"""The lab's Collector, in plain Python (Chapter 7).

Each function does what one OpenTelemetry Collector processor does,
on spans in otlp.load()'s plain shape, so every stage can be measured
and tested offline. collector/pronto-collector.yaml configures a real
Collector the same way.

  redact       the redaction processor: an allowlist of attribute
               keys, masks for values that look like personal data,
               and summary counts on each span
  tail_sample  the tail_sampling processor: keep a whole trace if any
               policy matches, after the trace is complete
  head_sample  what a ratio sampler in the SDK does instead: decide
               at the root, before anything has gone wrong
"""
import re
from collections import Counter

# The trace profile: what receipts, dashboards and the linter need
ALLOWED_KEYS = {
    "gen_ai.operation.name", "gen_ai.provider.name",
    "gen_ai.request.model", "gen_ai.response.model",
    "gen_ai.response.id", "gen_ai.response.finish_reasons",
    "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens",
    "gen_ai.usage.cache_read.input_tokens",
    "gen_ai.agent.id", "gen_ai.agent.name", "gen_ai.agent.version",
    "gen_ai.conversation.id", "gen_ai.tool.name", "gen_ai.tool.call.id",
    "gen_ai.tool.type", "gen_ai.data_source.id", "error.type",
    "pronto.tool.target", "pronto.tool.arguments_digest",
    "pronto.effect.status", "pronto.effect.ref",
    "pronto.effect.amount", "pronto.effect.currency",
    "pronto.source.version", "mcp.method.name", "mcp.session.id",
    "mcp.protocol.version", "jsonrpc.request.id", "network.transport",
    "messaging.system", "messaging.operation.type",
    "messaging.destination.name", "messaging.message.id"}
BLOCKED_VALUES = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),               # email
    re.compile(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b"),           # US phone
    re.compile(r"\b(?:\d[ -]?){13,16}\b")]                  # card
MASK = "****"
ERROR = 2                                   # OTLP status code


def redact(spans, allowed=ALLOWED_KEYS, blocked=BLOCKED_VALUES):
    """Drop keys off the allowlist. Mask blocked values."""
    out = []
    for s in spans:
        kept, dropped, masked = {}, 0, 0
        for key, value in s["attributes"].items():
            if key not in allowed:
                dropped += 1
                continue
            if isinstance(value, str):
                clean = value
                for pattern in blocked:
                    clean = pattern.sub(MASK, clean)
                masked += clean != value
                value = clean
            kept[key] = value
        if dropped:
            kept["redaction.redacted.count"] = dropped
        if masked:
            kept["redaction.masked.count"] = masked
        out.append({**s, "attributes": kept})
    return out


def traces(spans):
    grouped = {}
    for s in spans:
        grouped.setdefault(s["trace_id"], []).append(s)
    return grouped


def sampled(trace_id, rate):
    """Deterministic, from the trace ID: the same answer everywhere."""
    return int(trace_id[16:], 16) < rate * 2 ** 64


def why_keep(members, rate, slow_s):
    """The first policy that matches this trace, or None."""
    if any(s["status"] == ERROR for s in members):
        return "error"
    if any("pronto.effect.status" in s["attributes"]
           for s in members):
        return "action"
    took = max(s["end"] for s in members) - min(
        s["start"] for s in members)
    if took >= slow_s * 1e9:
        return "slow"
    if sampled(members[0]["trace_id"], rate):
        return "baseline"
    return None


def tail_sample(spans, rate=0.10, slow_s=30):
    """Keep whole traces: every error, every action, every slow turn,
    and a share of the rest. Returns (kept spans, reasons)."""
    reasons, kept = Counter(), []
    for members in traces(spans).values():
        reason = why_keep(members, rate, slow_s)
        if reason:
            reasons[reason] += 1
            kept += members
    return kept, reasons


def head_sample(spans, rate=0.10):
    """Decide at the root, from the trace ID alone."""
    return [s for s in spans if sampled(s["trace_id"], rate)]


def incidents(spans, slow_s=30):
    """Trace IDs of turns someone will investigate: errors and slow."""
    return {tid for tid, members in traces(spans).items()
            if why_keep(members, 0, slow_s) in ("error", "slow")}


def leaks(spans, canaries):
    """Attribute values that contain a canary: a name, email or phone."""
    return sum(1 for s in spans for v in s["attributes"].values()
               if isinstance(v, str) and any(c in v for c in canaries))
