"""Speedy hands a card dispute to PayCo's Ledger agent over A2A
(Chapter 5).

The A2A request travels as HTTP headers and a JSON body, so trace
context rides in the W3C traceparent header. PayCo is another
company: Ledger records its work in PayCo's own backend, starts its
own trace and links it to Pronto's span, and returns its task ID and
trace ID so Pronto can join the two.
"""
import json

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind

from telemetry.propagation import inject, remote_span_context

LEDGER_CARD = {"name": "Ledger", "id": "agent://payco/ledger",
               "version": "4.2.0", "url": "https://a2a.payco.example"}


class A2AClient:
    """Pronto's side of one A2A conversation with a remote agent."""

    def __init__(self, world, tracer, remote, card):
        self.world, self.tracer = world, tracer
        self.remote, self.card = remote, card

    def send(self, text, data, conversation_id):
        self.world.clock.advance(0.01)
        span = self.tracer.start_span(
            f"invoke_agent {self.card['name']}", kind=SpanKind.CLIENT,
            attributes={"gen_ai.operation.name": "invoke_agent",
                        "gen_ai.agent.name": self.card["name"],
                        "gen_ai.agent.id": self.card["id"],
                        "gen_ai.agent.version": self.card["version"],
                        "gen_ai.conversation.id": conversation_id,
                        "server.address": self.card["url"]},
            start_time=self.world.clock.now())
        with trace.use_span(span, end_on_exit=False):
            headers = inject({"A2A-Version": "1.0"})
            body = json.dumps({"jsonrpc": "2.0", "id": "1",
                               "method": "SendMessage", "params": {
                                   "message": {"messageId": "msg_a301",
                                               "role": "ROLE_USER",
                                               "parts": [
                                                   {"text": text},
                                                   {"data": data}]}}})
            self.world.clock.advance(0.05)
            reply = json.loads(self.remote.post(headers, body))
            task = reply["result"]["task"]
            self.world.clock.advance(0.05)
            span.set_attributes({
                "pronto.a2a.task_id": task["id"],
                "pronto.a2a.remote_trace_id":
                    task["metadata"]["trace_id"]})
            span.end(end_time=self.world.clock.now())
        return task


class Ledger:
    """PayCo's dispute agent. Its spans go to PayCo's backend."""

    def __init__(self, world, tracer, orders):
        self.world, self.tracer, self.orders = world, tracer, orders

    def post(self, headers, body):
        message = json.loads(body)["params"]["message"]
        data = message["parts"][1]["data"]
        caller = remote_span_context(headers)
        # Trust boundary: PayCo's own trace, linked to Pronto's
        span = self.tracer.start_span(
            "invoke_agent Ledger", context=Context(),
            kind=SpanKind.INTERNAL,
            links=[Link(caller, {"pronto.link": "a2a_caller"})],
            attributes={"gen_ai.operation.name": "invoke_agent",
                        "gen_ai.agent.name": "Ledger",
                        "gen_ai.agent.id": LEDGER_CARD["id"],
                        "gen_ai.agent.version": LEDGER_CARD["version"]},
            start_time=self.world.clock.now())
        with trace.use_span(span, end_on_exit=False):
            order = self.orders.call("orders.get",
                                     {"order_id": data["order_id"]})
            self.world.clock.advance(2.4)        # Ledger's own work
            dispute = "dp_4410" if order["status"] else None
            span.end(end_time=self.world.clock.now())
        trace_id = f"{span.get_span_context().trace_id:032x}"
        return json.dumps({"jsonrpc": "2.0", "id": "1", "result": {
            "task": {"id": "tsk_7q2m", "contextId": "ctx_payco_19b2",
                     "status": {"state": "TASK_STATE_COMPLETED"},
                     "artifacts": [{"artifactId": "art_1", "parts": [
                         {"data": {"dispute": dispute}}]}],
                     "metadata": {"trace_id": trace_id}}}})
