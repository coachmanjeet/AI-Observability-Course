"""An async hand-off: Speedy queues a confirmation that a worker
sends minutes later (Chapter 5).

The message carries trace context in its headers. The worker starts
a new trace for its own work and links it to the span that queued
the message, as the OpenTelemetry messaging conventions recommend
when the processing happens long after the send.
"""
from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, use_span

from telemetry.propagation import inject, remote_span_context

QUEUE = "notifications"


class Queue:
    def __init__(self, world, tracer):
        self.world, self.tracer, self.messages = world, tracer, []

    def send(self, body):
        message_id = f"msg_{len(self.messages) + 801:04d}"
        self.world.clock.advance(0.01)
        span = self.tracer.start_span(
            f"send {QUEUE}", kind=SpanKind.PRODUCER, attributes={
                "messaging.system": "pronto-queue",
                "messaging.operation.type": "send",
                "messaging.destination.name": QUEUE,
                "messaging.message.id": message_id},
            start_time=self.world.clock.now())
        with use_span(span, end_on_exit=False):
            self.messages.append({"id": message_id, "body": body,
                                  "headers": inject({})})
            self.world.clock.advance(0.02)
            span.end(end_time=self.world.clock.now())
        return {"ref": f"message:{message_id}", "status": "queued"}


def deliver(world, tracer, queue):
    """The notifier worker: send each queued message, later."""
    for message in queue.messages:
        sent = remote_span_context(message["headers"])
        span = tracer.start_span(
            f"process {QUEUE}", context=Context(),
            kind=SpanKind.CONSUMER, links=[Link(sent)],
            attributes={"messaging.system": "pronto-queue",
                        "messaging.operation.type": "process",
                        "messaging.destination.name": QUEUE,
                        "messaging.message.id": message["id"]},
            start_time=world.clock.now())
        world.clock.advance(0.9)                 # the SMS gateway
        span.end(end_time=world.clock.now())
