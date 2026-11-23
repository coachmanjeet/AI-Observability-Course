"""Decision traces as a graph (Chapter 5).

Usage: python -m decisions.graph TRACE.json why [FILTER]
       python -m decisions.graph TRACE.json used SOURCE[@VERSION]

Speedy's spans carry two kinds of span link, named by the pronto.link
attribute. A tool call is decided_by the model call that asked for
it, and a model call has every tool result it could see in_context.
Tool spans that read a record carry the record's source ID and
version. Followed together, they lead from every action back to the
versioned records it rested on.
"""
import argparse
from datetime import datetime, timezone

from pronto.tools import TOOLS
from telemetry import otlp


def stamp(ns):
    t = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)
    return t.strftime("%m-%d %H:%M:%S")


def linked(span, by_id, kind):
    return [by_id[link["span_id"]] for link in span["links"]
            if link["attributes"].get("pronto.link") == kind
            and link["span_id"] in by_id]


def actions(spans):
    """Consequential tool calls, in the order they ran."""
    return [s for s in spans
            if s["attributes"].get("gen_ai.operation.name")
            == "execute_tool" and "mcp.method.name" not in s["attributes"]
            and TOOLS[s["attributes"]["gen_ai.tool.name"]].side_effect]


def decision(action, by_id):
    """(the model call that asked, the records it saw)."""
    asked = linked(action, by_id, "decided_by")
    if not asked:
        return None
    reads = [s for s in linked(asked[0], by_id, "in_context")
             if "gen_ai.data_source.id" in s["attributes"]]
    return asked[0], reads


def source(read):
    a = read["attributes"]
    return a["gen_ai.data_source.id"], a["pronto.source.version"]


def outcome(action):
    a = action["attributes"]
    return a.get("pronto.effect.ref") or a.get("error.type", "read")


def why(spans, match=""):
    """The decision behind each action whose tool or target matches."""
    by_id = {s["span_id"]: s for s in spans}
    lines, covered, chosen = [], 0, 0
    for act in actions(spans):
        a = act["attributes"]
        found = decision(act, by_id)
        covered += found is not None
        if match not in (a["gen_ai.tool.name"], a["pronto.tool.target"],
                         ""):
            continue
        chosen += 1
        lines.append(f"{stamp(act['start'])}  {a['gen_ai.tool.name']} "
                     f"{a['pronto.tool.target']} -> {outcome(act)}")
        if found is None:
            lines.append("  no decision trace")
            continue
        asked, reads = found
        m = asked["attributes"]
        lines.append(f"  decided by chat {m['gen_ai.request.model']}"
                     f" ({m['gen_ai.response.id']}) at "
                     f"{stamp(asked['end'])[6:]}")
        if not reads:
            lines.append("  knew only the customer's message")
        for read in reads:
            sid, version = source(read)
            tool = read["attributes"]["gen_ai.tool.name"]
            lines.append(f"  {sid:<16} {version:<11} {tool:<14}"
                         f" {stamp(read['end'])[6:]}")
    lines.append(f"{covered} of {len(actions(spans))} actions have a "
                 f"decision trace; showing {chosen}")
    return "\n".join(lines)


def used(spans, query):
    """Every action decided with this source (and version) in view."""
    want, _, want_version = query.partition("@")
    by_id = {s["span_id"]: s for s in spans}
    groups = {}
    for act in actions(spans):
        found = decision(act, by_id)
        for read in (found[1] if found else []):
            sid, version = source(read)
            if sid == want and want_version in ("", version):
                groups.setdefault(version, []).append(act)
    lines = []
    for version, acts in sorted(groups.items()):
        lines.append(f"{want} @ {version}: {len(acts)} "
                     f"action{'s' * (len(acts) != 1)}")
        for act in acts:
            a = act["attributes"]
            lines.append(f"  {stamp(act['start'])}  "
                         f"{a['gen_ai.tool.name']:<15} "
                         f"{a['pronto.tool.target']:<15} {outcome(act)}")
    return "\n".join(lines) or f"no action used {query}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("trace")
    parser.add_argument("query", choices=["why", "used"])
    parser.add_argument("subject", nargs="?", default="")
    args = parser.parse_args(argv)
    spans = otlp.load(args.trace)
    if args.query == "why":
        print(why(spans, args.subject))
    else:
        print(used(spans, args.subject))


if __name__ == "__main__":
    main()
