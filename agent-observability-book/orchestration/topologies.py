"""One task, four orchestration topologies (Chapter 17).

The task is Saturday's conversation: refund the spoiled
strawberries, confirm by text, then deal with the double card
charge. Each topology wires the same agents differently. A
topology is data: the parts, what each part can call, and the
hops one run of the task takes. score.py reads that data and
the receipts a run writes.
"""
from dataclasses import dataclass

# Consequential tools and their side-effect class (Chapter 2)
CONSEQUENTIAL = {"orders.get": "read_sensitive",
                 "refunds.create": "financial",
                 "notify.send": "external_communication",
                 "disputes.open": "financial",
                 "substitutions.write": "write",
                 "contacts.export": "read_sensitive",
                 "campaigns.send": "external_communication"}


@dataclass(frozen=True)
class Part:
    name: str
    runs_on: str            # "code" or "model"
    owner: str              # who runs it: "pronto" or "payco"
    tools: tuple = ()       # consequential tools it calls
    instructs: tuple = ()   # parts it can send instructions to


@dataclass(frozen=True)
class Hop:
    actor: str              # the part that acts
    tool: str               # a tool, or "agent:<Part>"
    via: str                # direct, mcp, a2a or queue
    gate: str = ""          # Pronto enforcement point, if any
    routed_by: str = ""     # "code" or "model" chose this hop
    keeps_context: bool = True   # carries the request's context


SPEEDY = Part("Speedy", "model", "pronto",
              ("orders.get", "refunds.create", "notify.send"))
LEDGER = Part("Ledger", "model", "payco",
              ("orders.get", "disputes.open"))
PICK = Part("Pick", "model", "pronto", ("substitutions.write",))
PROMO = Part("Promo", "model", "promo-co",
             ("contacts.export", "campaigns.send"))

MCP = "gateway://pronto/mcp-gateway-us-west"
A2A = "gateway://pronto/a2a-gateway-us-west"
NOTIFY = "queue://pronto/notify"


def _refund(routed_by):
    """Speedy's part of the task, the same in every topology."""
    return [Hop("Speedy", "orders.get", "mcp", MCP, routed_by),
            Hop("Speedy", "refunds.create", "mcp", MCP,
                "model"),
            Hop("Speedy", "notify.send", "queue", NOTIFY,
                "model")]


def _ledger(keeps_context=True):
    return [Hop("Ledger", "orders.get", "mcp", MCP, "model",
                keeps_context),
            Hop("Ledger", "disputes.open", "direct", "",
                "model", keeps_context)]


def router():
    """Code reads the intent and calls one specialist."""
    parts = {"Router": Part("Router", "code", "pronto", (),
                            ("Speedy", "Ledger")),
             "Speedy": SPEEDY, "Ledger": LEDGER}
    hops = (_refund("code")
            + [Hop("Router", "agent:Ledger", "a2a", A2A,
                   "code")]
            + _ledger())
    return "router", "Router", parts, hops


def supervisor():
    """A model plans and calls each specialist as a tool."""
    parts = {"Concierge": Part("Concierge", "model", "pronto",
                               (), ("Speedy", "Ledger")),
             "Speedy": SPEEDY, "Ledger": LEDGER}
    hops = ([Hop("Concierge", "agent:Speedy", "direct", "",
                 "model")]
            + _refund("model")
            + [Hop("Concierge", "agent:Ledger", "a2a", A2A,
                   "model")]
            + _ledger())
    return "supervisor", "Concierge", parts, hops


def handoff():
    """Speedy answers first, then hands the whole conversation
    to Ledger, which answers the customer from then on."""
    speedy = Part("Speedy", "model", "pronto", SPEEDY.tools,
                  ("Ledger",))
    parts = {"Speedy": speedy, "Ledger": LEDGER}
    hops = (_refund("code")
            + [Hop("Speedy", "agent:Ledger", "a2a", A2A,
                   "model")]
            + _ledger())
    return "handoff", "Speedy", parts, hops


def broker(forward_context=False):
    """Speedy posts the dispute to a broker, which picks an
    agent from the registry at run time. By default the broker
    re-issues the task as itself, as many brokers do."""
    speedy = Part("Speedy", "model", "pronto", SPEEDY.tools,
                  ("Broker",))
    parts = {"Broker": Part("Broker", "model", "pronto", (),
                            ("Speedy", "Ledger", "Pick",
                             "Promo")),
             "Speedy": speedy, "Ledger": LEDGER, "Pick": PICK,
             "Promo": PROMO}
    hops = (_refund("code")
            + [Hop("Speedy", "agent:Broker", "direct", "",
                   "model"),
               Hop("Broker", "agent:Ledger", "a2a", A2A,
                   "model", forward_context)]
            + _ledger(forward_context))
    return "broker", "Speedy", parts, hops


TOPOLOGIES = [router, supervisor, handoff, broker]
