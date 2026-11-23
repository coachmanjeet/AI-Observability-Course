"""W3C trace context across process boundaries (Chapter 4).

inject() writes the current span's context into a carrier: MCP's
params._meta, an A2A request's HTTP headers or a queue message's
headers. extract() reads it back on the other side.
"""
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator)

W3C = TraceContextTextMapPropagator()


def inject(carrier):
    """Add traceparent (and tracestate) to a dict, then return it."""
    W3C.inject(carrier)
    return carrier


def extract(carrier):
    """The remote context in a carrier, as an OpenTelemetry Context."""
    return W3C.extract(carrier)


def remote_span_context(carrier):
    """The caller's span context, for a span link."""
    return trace.get_current_span(extract(carrier)).get_span_context()
