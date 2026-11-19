"""A deterministic stand-in for a tool-calling model (Chapter 4).

MockModel decides the way a careful support model would under Book 1's
refund policy: read the order, check the photo and the policy, then
refund the item's value or hand the case to a person. Each decision
costs a fixed number of tokens and seconds, so every trace in the book
comes out the same. careless=True skips the $50 check, which lets the
refund tool's own rule show up in the trace as an error.
"""
import pathlib
from dataclasses import dataclass, field

SYSTEM = (pathlib.Path(__file__).parent / "prompts" /
          "speedy-system.md").read_text(encoding="utf-8")

# decision: (input tokens, output tokens, seconds)
COSTS = {"lookup": (2410, 96, 3.87), "verify": (2560, 88, 4.27),
         "refund": (3120, 410, 19.24), "escalate": (3120, 352, 16.80),
         "reply": (3390, 62, 3.11), "notify": (3290, 58, 2.36),
         "dispute": (2280, 74, 3.02), "status": (2440, 40, 2.05)}
CACHE_READ = 1800                   # system prompt and tool definitions
CALL_IDS = ["call_8c20", "call_9d01", "call_9d02", "call_8c21",
            "call_8c22", "call_8c23"]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Reply:
    id: str
    model: str
    text: str = ""
    tool_calls: list = field(default_factory=list)
    finish_reason: str = "stop"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = CACHE_READ
    seconds: float = 0.0
    messages: list = field(default_factory=list)   # what it was sent
    system: str = ""


class MockModel:
    provider = "mock"
    name = "pronto-mock-1"

    def __init__(self, clock=None, careless=False, call_ids=CALL_IDS):
        self.clock, self.careless = clock, careless
        self.calls = iter(call_ids)
        self.turn = 0

    def complete(self, messages):
        reply = self._decide(messages)
        reply.messages, reply.system = list(messages), SYSTEM
        if self.clock:
            self.clock.advance(reply.seconds)   # models take time
        return reply

    def _decide(self, messages):
        task = messages[0]["task"]
        seen = {m["tool"]: m for m in messages if m["role"] == "tool"}
        self.turn += 1
        if task.get("intent") == "dispute":
            return self._dispute(task, seen)
        if "orders.get" not in seen:
            return self._call("lookup", ("orders.get",
                              {"order_id": task["order_id"]}))
        lookup = seen["orders.get"]["result"]
        if lookup.get("error") == "NotFound":    # Chapter 7
            return self._text("status", "I couldn't find that order. "
                              "Could you check the order number?")
        if "error" in lookup:
            return self._text("status", "I can't reach our order "
                              "system right now. Please try again soon.")
        if task.get("intent") == "status":       # Chapter 7
            return self._text("status", "Your order is "
                              f"{lookup['status']}.")
        if "photos.verify" not in seen:
            return self._call("verify", ("policy.lookup", {}),
                              ("photos.verify",
                               {"photo_id": task["photo_id"]}))
        done = seen.get("refunds.create") or seen.get("cases.escalate")
        if done and task.get("notify") and "notify.queue" not in seen \
                and "ref" in done["result"]:
            return self._call("notify", ("notify.queue", {
                "customer_id": task["customer_id"],
                "template": "refund_confirmation",
                "order_id": task["order_id"]}))
        if done:
            return self._reply(done)
        order, policy = seen["orders.get"], seen["policy.lookup"]
        photo = seen["photos.verify"]["result"]
        if not (photo["shows_spoilage"] and photo["hours_after_delivery"]
                <= policy["result"]["photo_window_hours"]):
            return self._text("reply", "Spoiled items need a photo "
                              "within 24 hours of delivery.")
        cents = order["result"]["value_cents"]
        if cents > policy["result"]["approval_above_cents"] \
                and not self.careless:
            return self._call("escalate", ("cases.escalate", {
                "order_id": task["order_id"],
                "reason": "refund over $50"}))
        return self._call("refund", ("refunds.create", {
            "order_id": task["order_id"], "amount": f"{cents / 100:.2f}",
            "currency": "USD", "reason": "spoiled_perishable",
            "photo": True}))

    def _dispute(self, task, seen):
        if "disputes.open" not in seen:
            return self._call("dispute", ("disputes.open", {
                "order_id": task["order_id"],
                "reason": "duplicate_charge"}))
        ref = seen["disputes.open"]["result"].get("ref", "")
        return self._text("reply", "PayCo has opened dispute "
                          f"{ref.split(':')[-1]} for the double charge.")

    def _usage(self, decision, reply):
        reply.input_tokens, reply.output_tokens, reply.seconds = \
            COSTS[decision]
        return reply

    def _call(self, decision, *calls):
        reply = Reply(id=f"resp_{self.turn:02d}", model=self.name,
                      finish_reason="tool_calls",
                      tool_calls=[ToolCall(next(self.calls), n, a)
                                  for n, a in calls])
        return self._usage(decision, reply)

    def _text(self, decision, text):
        reply = Reply(id=f"resp_{self.turn:02d}", model=self.name,
                      text=text)
        return self._usage(decision, reply)

    def _reply(self, done):
        if "error" in done["result"]:
            return self._text("reply", "I couldn't issue that refund. "
                              "A teammate will review it.")
        if done["tool"] == "cases.escalate":
            return self._text("reply", "A teammate will review this "
                              "refund shortly.")
        value = done["result"]["amount"]["value"]
        return self._text("reply", f"Done! I've refunded ${value}.")
