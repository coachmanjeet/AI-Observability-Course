"""Speedy's tools, under the names Pronto registers them with.

Book 1's four tools keep their behavior and get namespaced names:
lookup_policy is policy.lookup, get_order_status is orders.get,
issue_refund is refunds.create and escalate_to_human is
cases.escalate. photos.verify is new. Each tool is tagged with a
consequence class (Chapter 2) and names its target argument, so the
trace can say what each call touched without copying its content.
"""
from dataclasses import dataclass
from decimal import Decimal


class ToolError(Exception):
    """The tool refused or failed. The span records it as an error."""


class ApprovalRequired(ToolError):
    """Over the $50 rule: a person must approve (Book 1's rung 3)."""


class AlreadyRefunded(ToolError):
    """Never refund the same order twice."""


class AboveItemValue(ToolError):
    """Never refund more than the item cost."""


class NotFound(ToolError):
    """No such record. The message never echoes what was asked for."""


class Unavailable(ToolError):
    """A system of record didn't answer in time."""


def to_cents(amount):
    return int(Decimal(amount) * 100)


def policy_lookup(world, args):
    return dict(world.policy)


def orders_get(world, args):
    if args["order_id"] not in world.orders:
        raise NotFound("no such order")
    return dict(world.orders[args["order_id"]])


def photos_verify(world, args):
    return dict(world.photos[args["photo_id"]])


def refunds_create(world, args):
    order = world.orders[args["order_id"]]
    cents = to_cents(args["amount"])
    if cents > world.policy["approval_above_cents"]:
        raise ApprovalRequired(f"{args['amount']} is over the $50 rule")
    if cents > order["value_cents"]:
        raise AboveItemValue(f"{args['amount']} is above the item value")
    refund_id = f"rf_{world.refund_seq}"
    try:
        world.db.execute("INSERT INTO refunds VALUES (?,?,?)",
                         (refund_id, args["order_id"], cents))
    except Exception:
        raise AlreadyRefunded(args["order_id"]) from None
    world.refund_seq += 1
    return {"ref": f"refund:{refund_id}", "status": "succeeded",
            "amount": {"value": args["amount"],
                       "currency": args["currency"]}}


def cases_escalate(world, args):
    count = world.db.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    case_id = f"case_{221 + count}"
    world.db.execute("INSERT INTO cases VALUES (?,?,?)",
                     (case_id, args["order_id"], args["reason"]))
    return {"ref": f"case:{case_id}", "status": "succeeded"}


@dataclass(frozen=True)
class Tool:
    run: object
    target: str | None          # the argument that names what it touches
    side_effect: str | None     # Chapter 2's consequence class
    reason: str = ""
    latency_s: float = 0.1


TOOLS = {
    "policy.lookup": Tool(policy_lookup, None, None, latency_s=0.08),
    "orders.get": Tool(orders_get, "order_id", "read_sensitive",
                       "Reads a customer's order, which holds personal data",
                       latency_s=0.14),
    "photos.verify": Tool(photos_verify, "photo_id", None, latency_s=7.49),
    "refunds.create": Tool(refunds_create, "order_id", "financial",
                           "Issues a refund to the customer's card",
                           latency_s=1.11),
    "cases.escalate": Tool(cases_escalate, "order_id", "write",
                           "Opens a case for a person to review",
                           latency_s=0.62),
    # Remote only: reached through world.routes (Chapter 4)
    "notify.queue": Tool(None, "customer_id", "external_communication",
                         "Queues a message to the customer"),
    "disputes.open": Tool(None, "order_id", "external_communication",
                          "Hands a card dispute to PayCo's Ledger agent"),
}


def target(tool, args):
    """'order:ord_5521' for {'order_id': 'ord_5521'}."""
    key = TOOLS[tool].target
    return f"{key.removesuffix('_id')}:{args[key]}" if key else None


def run_tool(world, call):
    """Run one tool call. Refusals come back as results, not crashes,
    so the model can explain them to the customer."""
    tool, route = TOOLS[call.name], world.routes.get(call.name)
    try:
        if route:                    # over MCP, A2A or a queue (Ch 4)
            return route(call.arguments)
        world.clock.advance(tool.latency_s)
        return tool.run(world, call.arguments)
    except ToolError as error:
        return {"error": type(error).__name__, "message": str(error)}
