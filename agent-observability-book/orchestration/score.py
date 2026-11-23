"""Score topologies by their governance cost (Chapter 17).

Usage: python -m orchestration.score [OUT_DIR]

Runs the same task through each topology in topologies.py and
measures what the wiring does to governance: how many
consequential calls pass a Pronto gate, how many routing choices
a model makes, how many consequential tools the entry point can
reach, whether each hop still names the customer, and whose
systems the task touches. It also writes the receipt chain each
run would produce, linked by parent_receipt_id.
"""
import json
import pathlib
import sys

from orchestration.topologies import (CONSEQUENTIAL, TOPOLOGIES,
                                      broker)


def reach(entry, parts):
    """Consequential tools reachable from the entry part."""
    seen, todo, tools = set(), [entry], set()
    while todo:
        name = todo.pop()
        if name in seen or name not in parts:
            continue
        seen.add(name)
        tools |= set(parts[name].tools)
        todo += list(parts[name].instructs)
    return tools, {parts[n].owner for n in seen} - {"pronto"}


def chain(name, hops):
    """One receipt per hop, linked to the hop that caused it."""
    out, parent, issuer = [], {}, {}
    for i, h in enumerate(hops):
        rid = f"rcpt_{name}_{i:02d}"
        by = issuer.get(h.actor, h.actor).lower()
        who = ("cust_7f3a91" if h.keeps_context
               else f"agent://pronto/{by}")
        out.append({"receipt_id": rid,
                    "who": {"agent_id": h.actor},
                    "for_whom": {"principal_id": who},
                    "did_what": {"action": {"tool": h.tool,
                                            "via": h.via}},
                    "evidence": {"parent_receipt_id":
                                 parent.get(h.actor)}})
        if h.tool.startswith("agent:"):
            parent[h.tool[6:]] = rid
            if not h.keeps_context:
                issuer[h.tool[6:]] = h.actor
    return out


def score(topology):
    name, entry, parts, hops = topology()
    calls = [h for h in hops if h.tool in CONSEQUENTIAL]
    gated = sum(bool(h.gate) for h in calls)
    routes = sum(h.routed_by == "model"
                 for h in hops if h.tool.startswith("agent:"))
    tools, outside = reach(entry, parts)
    named = sum(h.keeps_context for h in hops)
    return {"topology": name, "gated": f"{gated}/{len(calls)}",
            "model_routes": routes, "reach": len(tools),
            "named": f"{named}/{len(hops)}",
            "outside": sorted(outside),
            "receipts": chain(name, hops)}


def rows():
    runs = [score(t) for t in TOPOLOGIES]
    ctx = score(lambda: broker(forward_context=True))
    ctx["topology"] = "broker+ctx"
    return runs + [ctx]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    runs = rows()
    print("One task: refund, confirm, open a dispute")
    print(f"{'':<12}{'gated':>6}{'model':>7}{'reach':>7}"
          f"{'customer':>10}  outside")
    print(f"{'':<12}{'calls':>6}{'routes':>7}{'tools':>7}"
          f"{'named':>10}  Pronto")
    for r in runs:
        print(f"{r['topology']:<12}{r['gated']:>6}"
              f"{r['model_routes']:>7}{r['reach']:>7}"
              f"{r['named']:>10}  {', '.join(r['outside'])}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        for r in runs:
            (out / f"{r['topology']}.json").write_text(
                json.dumps(r, indent=2) + "\n")
        refund = next(x for x in runs[0]["receipts"]
                      if x["did_what"]["action"]["tool"]
                      == "refunds.create")
        via = refund["did_what"]["action"]["via"]
        (out / "via.json").write_text(json.dumps(
            {"did_what": {"action": {"via": via}}},
            indent=2) + "\n")


if __name__ == "__main__":
    main()
