"""OpenTelemetry GenAI spans for an agent loop (Chapter 4).

One helper per span type in the GenAI semantic conventions:
invoke_agent for an agent's turn, chat for each model call, and
execute_tool for each tool call. Names and attributes follow the
conventions as of November 2026 (Development stability).
Attributes in the pronto.* namespace are Pronto's own. They carry
what a receipt needs, as digests and references, never content.
"""
import json
import os
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Link, SpanKind, Status, StatusCode

from pronto.tools import TOOLS, target
from receipts.tools import digest

CAPTURE = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"


def capture_content():
    """Content capture is opt-in, as the conventions require."""
    value = os.environ.get(CAPTURE, "false").lower()
    return value in ("true", "span_only", "span_and_event")


def _message(m):
    """One message in the conventions' shape, for opt-in capture."""
    if m["role"] == "user":
        return {"role": "user", "parts": [
            {"type": "text", "content": m["task"].get("message", "")}]}
    if m["role"] == "assistant":
        r = m["reply"]
        parts = [{"type": "tool_call", "id": c.id, "name": c.name,
                  "arguments": c.arguments} for c in r.tool_calls]
        if r.text:
            parts.append({"type": "text", "content": r.text})
        return {"role": "assistant", "parts": parts}
    return {"role": "tool", "parts": [
        {"type": "tool_call_response", "response": m["result"]}]}


DECIDED_BY = {"pronto.link": "decided_by"}      # Chapter 6
IN_CONTEXT = {"pronto.link": "in_context"}


class GenAISpans:
    def __init__(self, tracer, clock, decisions=False):
        self.tracer, self.clock = tracer, clock
        self.decisions = decisions               # Chapter 6
        self.context, self.asked = [], None

    def _edges(self, op):
        """Chapter 6: a model call links to each tool result in
        its context. A tool call links to the one that asked."""
        if not self.decisions:
            return ()
        if op == "chat":
            return [Link(c, IN_CONTEXT) for c in self.context]
        if op == "execute_tool" and self.asked:
            return [Link(self.asked, DECIDED_BY)]
        return ()

    def _remember(self, op, span):
        if op == "invoke_agent":                 # a new turn
            self.context, self.asked = [], None
        elif op == "chat":
            self.asked = span.get_span_context()
        elif op == "execute_tool":
            self.context.append(span.get_span_context())

    @contextmanager
    def _span(self, name, kind, attributes):
        self.clock.advance(0.01)                 # loop overhead
        op = attributes["gen_ai.operation.name"]
        span = self.tracer.start_span(
            name, kind=kind, attributes=attributes,
            links=self._edges(op), start_time=self.clock.now())
        self._remember(op, span)
        with trace.use_span(span, end_on_exit=False):
            try:
                yield span
            finally:
                span.end(end_time=self.clock.now())

    def agent(self, agent, conversation_id):
        name = f"invoke_agent {agent['name']}"
        return self._span(name, SpanKind.INTERNAL, {
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.id": agent["id"],
            "gen_ai.agent.name": agent["name"],
            "gen_ai.agent.version": agent["version"],
            "gen_ai.conversation.id": conversation_id})

    def chat(self, model, conversation_id):
        name = f"chat {model.name}"
        return self._span(name, SpanKind.CLIENT, {
            "gen_ai.operation.name": "chat",
            "gen_ai.provider.name": model.provider,
            "gen_ai.request.model": model.name,
            "gen_ai.conversation.id": conversation_id})

    def tool(self, call, conversation_id):
        attributes = {"gen_ai.operation.name": "execute_tool",
                      "gen_ai.tool.name": call.name,
                      "gen_ai.tool.call.id": call.id,
                      "gen_ai.tool.type": "function",
                      "gen_ai.conversation.id": conversation_id}
        if TOOLS[call.name].side_effect:         # consequential
            attributes.update({
                "pronto.tool.target":
                    target(call.name, call.arguments),
                "pronto.tool.arguments_digest":
                    digest(call.arguments)})
        if capture_content():
            attributes["gen_ai.tool.call.arguments"] = \
                json.dumps(call.arguments)
        name = f"execute_tool {call.name}"
        return self._span(name, SpanKind.INTERNAL, attributes)

    @staticmethod
    def record_reply(span, reply):
        span.set_attributes({
            "gen_ai.response.id": reply.id,
            "gen_ai.response.model": reply.model,
            "gen_ai.response.finish_reasons":
                [reply.finish_reason],
            "gen_ai.usage.input_tokens": reply.input_tokens,
            "gen_ai.usage.output_tokens": reply.output_tokens,
            "gen_ai.usage.cache_read.input_tokens":
                reply.cache_read_tokens})
        if capture_content():                    # opt-in, Chapter 7
            span.set_attributes({
                "gen_ai.system_instructions": json.dumps(
                    [{"type": "text", "content": reply.system}]),
                "gen_ai.input.messages": json.dumps(
                    [_message(m) for m in reply.messages]),
                "gen_ai.output.messages": json.dumps(
                    [_message({"role": "assistant", "reply": reply})])})

    @staticmethod
    def record_result(span, result):
        if "error" in result:                    # refused
            span.set_status(Status(StatusCode.ERROR,
                                   result["message"]))
            span.set_attributes({
                "error.type": result["error"],
                "pronto.effect.status": "blocked"})
        elif "ref" in result:                    # changed state
            span.set_attributes({
                "pronto.effect.status": "succeeded",
                "pronto.effect.ref": result["ref"]})
            if "amount" in result:
                amount = result["amount"]
                span.set_attributes({
                    "pronto.effect.amount": amount["value"],
                    "pronto.effect.currency":
                        amount["currency"]})
        source = result.get("source")
        if source:                               # Chapter 6
            span.set_attributes({
                "gen_ai.data_source.id": source["id"],
                "pronto.source.version": source["version"]})
        if capture_content():
            span.set_attribute("gen_ai.tool.call.result",
                               json.dumps(result))
