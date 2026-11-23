"""Chapter 11: find every agent, MCP server and API from evidence.

Seven sources, one JSON file each in registry/evidence/. The scanner
joins them on three keys (agent ID, credential and host), decides
which actors are agents, and compares them with today's inventory.

Usage: python -m registry.discover registry/evidence [OUT_DIR]
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
INVENTORY = HERE.parent / "maturity" / "fleet.json"
SOURCES = ["cloud", "gateway", "api", "idp", "endpoint", "egress",
           "vendor"]
KINDS = {"1P": "first_party", "3P": "third_party",
         "shadow": "shadow"}
EFFECTS = {"orders.get": "read_sensitive",
           "refunds.create": "financial",
           "cases.escalate": "write",
           "substitutions.set": "write",
           "dispatch.assign": "write",
           "customers.export": "read_sensitive",
           "message/send": "external_communication",
           "POST /refunds": "financial",
           "POST /inventory/adjust": "write",
           "git push catalog-service": "write"}


def load(folder):
    """{source: rows} for the seven evidence files."""
    folder = pathlib.Path(folder)
    return {s: json.loads((folder / f"{s}.json").read_text())["rows"]
            for s in SOURCES}


def slug(name):
    """'night-owl/0.2' and 'Night Owl' both become 'night-owl'."""
    return name.split("/")[0].strip().lower().replace(" ", "-")


def actor(actors, key, **facts):
    a = actors.setdefault(key, {
        "key": key, "agent_id": None, "name": None, "sources": [],
        "credentials": [], "hosts": [], "calls": {}, "egress": 0,
        "mcp_servers": [], "role": None, "vendor": None})
    for k, v in facts.items():
        if v is not None and not a.get(k):
            a[k] = v
    return a


def seen(a, source, credential=None, host=None):
    for field, value in (("sources", source),
                         ("credentials", credential),
                         ("hosts", host)):
        if value and value not in a[field]:
            a[field].append(value)


def correlate(evidence, inventory):
    """Join the sources into actors, keyed by agent ID when known."""
    by_slug = {slug(x["name"]): x for x in inventory["agents"]}
    actors = {}
    for source in ("cloud", "gateway", "vendor"):
        for row in evidence[source]:
            a = actor(actors, row["agent_id"],
                      agent_id=row["agent_id"],
                      vendor=row.get("vendor"))
            seen(a, source, row.get("credential"),
                 row.get("runtime"))
            for tool, n in row.get("calls", {}).items():
                a["calls"][tool] = a["calls"].get(tool, 0) + n
    for row in evidence["api"]:
        known = by_slug.get(slug(row["client"]))
        key = known["agent_id"] if known else (
            "client:" + slug(row["client"]))
        a = actor(actors, key, agent_id=known and known["agent_id"])
        seen(a, "api", row["credential"], row["host"])
        a["calls"][row["endpoint"]] = (
            a["calls"].get(row["endpoint"], 0) + row["calls"])
        a["refused"] = a.get("refused", 0) + sum(
            n for code, n in row["status"].items() if code >= "400")
    for row in evidence["endpoint"]:
        for proc in row["processes"]:
            match = [a for a in actors.values()
                     if row["host"] in a["hosts"]
                     and slug(a["name"] or a["key"].split(":")[-1])
                     == proc]
            a = match[0] if match else actor(
                actors, f"process:{proc}@{row['host']}")
            seen(a, "endpoint", host=row["host"])
            a["role"] = row["role"]
            a["mcp_servers"] += row["mcp_servers"]
    for a in actors.values():
        name = by_slug.get(slug(a["key"].split(":")[-1]))
        known = next((x for x in inventory["agents"]
                      if x["agent_id"] == a["agent_id"]), name)
        a["name"] = known["name"] if known else (
            a["key"].split(":")[-1].split("@")[0]
            .replace("-", " ").title())
    hosts = {r["from"]: r["calls"] for r in evidence["egress"]}
    for a in actors.values():
        for h in a["hosts"]:
            if h in hosts:
                a["egress"] += hosts[h]
                seen(a, "egress")
    creds = {r["credential"]: r for r in evidence["idp"]}
    for a in actors.values():
        a["idp"] = [creds[c] for c in a["credentials"] if c in creds]
        if a["idp"]:
            seen(a, "idp")
    return list(actors.values())


def category(a):
    """agent, automation or ai_use, from what the evidence shows."""
    ai = a["egress"] > 0 or a["agent_id"] is not None
    acts = bool(a["calls"]) or any(m.get("target")
                                   for m in a["mcp_servers"])
    if ai and acts:
        return "agent"
    return "automation" if acts else "ai_use"


def flags(a, everyone):
    """Findings for one agent, in plain words."""
    out = []
    for cred in a["idp"]:
        others = [o["name"] for o in everyone if o is not a
                  and cred["credential"] in o["credentials"]]
        if cred["type"] == "person":
            out.append(f"runs on a person's credential "
                       f"({cred['owner']})")
        if cred["status"].startswith("revoked"):
            out.append(f"still running after {cred['credential']} "
                       f"was {cred['status']}")
            out.append(f"{a.get('refused', 0)} calls refused since")
        if others:
            out.append(f"shares {cred['credential']} with "
                       + ", ".join(others))
        out += [f"broad scope {s}" for s in cred["scopes"]
                if s.endswith(":all")]
    for m in a["mcp_servers"]:
        out.append(f"unregistered MCP server {m['name']} on "
                   f"{m['listen']}")
        out.append(f"{m['name']} reads {m['target']}")
    return out


def scan(evidence, inventory):
    """The whole discovery result as one dict."""
    actors = correlate(evidence, inventory)
    known = {x["agent_id"]: x for x in inventory["agents"]}
    agents = []
    for a in actors:
        a["category"] = category(a)
        if a["category"] != "agent":
            continue
        inv = known.get(a["agent_id"])
        a["agent_id"] = a["agent_id"] or (
            "agent://unregistered/" + slug(a["name"]))
        a["known"] = inv is not None
        a["registered"] = bool(inv and inv["registered"])
        a["kind"] = KINDS[inv["kind"]] if inv else (
            "third_party" if a["vendor"] else "shadow")
        a["owner"] = inv["owner"] if inv and inv["owner"] else None
        a["effects"] = sorted({EFFECTS[t] for t in a["calls"]
                               if t in EFFECTS})
        agents.append(a)
    for a in agents:
        a["flags"] = flags(a, actors)
    return {"rows": sum(len(r) for r in evidence.values()),
            "actors": actors, "agents": agents,
            "mcp_servers": mcp_servers(evidence, agents),
            "apis": apis(agents)}


def mcp_servers(evidence, agents):
    """Every MCP server seen anywhere, with who uses it."""
    found = {}
    for row in evidence["gateway"]:
        if not row["server"].startswith("a2a:"):
            found.setdefault(row["server"], ["gateway", set()])
    for row in evidence["vendor"]:
        if row.get("mcp_server"):
            found.setdefault(row["mcp_server"], ["vendor", set()])
    for a in agents:
        for row in evidence["gateway"]:
            if row["agent_id"] == a["agent_id"] and \
                    not row["server"].startswith("a2a:"):
                found[row["server"]][1].add(a["name"])
        for m in a["mcp_servers"]:
            found.setdefault(m["name"], ["endpoint", set()])
            found[m["name"]][1].add(a["name"])
    return [{"name": n, "seen_in": s, "clients": sorted(c)}
            for n, (s, c) in sorted(found.items())]


def apis(agents):
    """Consequential tools and endpoints, with the agents that call
    them and whether any caller is outside the registry."""
    table = {}
    for a in agents:
        for target, n in a["calls"].items():
            if target in EFFECTS:
                row = table.setdefault(target, {
                    "target": target, "effect": EFFECTS[target],
                    "callers": [], "unregistered": False})
                row["callers"].append(a["name"])
                row["unregistered"] |= not a["registered"]
    return sorted(table.values(), key=lambda r: r["target"])


def draft(a):
    """A draft registry record for an agent the inventory lacks."""
    return {"id": a["agent_id"], "name": a["name"],
            "version": "unknown", "kind": a["kind"],
            "owner": None, "state": "draft",
            "found_by": sorted(a["sources"]),
            "credentials": a["credentials"], "hosts": a["hosts"],
            "effects": a["effects"], "findings": a["flags"]}


def report(result):
    agents = result["agents"]
    new = [a for a in agents if not a["known"]]
    cats = [a["category"] for a in result["actors"]]
    lines = [f"Discovery, 2027-01-25 to 2027-01-31: 7 sources, "
             f"{result['rows']} rows",
             f"{len(cats)} actors: {cats.count('agent')} agents, "
             f"{cats.count('automation')} automation, "
             f"{cats.count('ai_use')} AI use with no actions", ""]
    for a in agents:
        status = "NEW" if not a["known"] else (
            "registered" if a["registered"] else "not registered")
        lines.append(f"{a['name']:<14}{a['kind']:<12}"
                     f"{len(a['sources'])} sources  {status}")
        lines += [f"  {f}" for f in a["flags"]]
    lines += ["", f"MCP servers: {len(result['mcp_servers'])} seen, "
              "0 in any inventory"]
    for m in result["mcp_servers"]:
        users = ", ".join(m["clients"]) or "-"
        lines.append(f"  {m['name']:<26}{m['seen_in']:<10}{users}")
    risky = [r for r in result["apis"] if r["unregistered"]]
    lines += ["", f"Consequential APIs, tools: "
              f"{len(result['apis'])}, {len(risky)} called by "
              "unregistered agents"]
    for r in risky:
        lines.append(f"  {r['target']:<24}{r['effect']:<10}"
                     + ", ".join(r["callers"]))
    lines += ["", f"Draft records: {len(new)} agents "
              f"({', '.join(a['name'] for a in new)})"]
    return "\n".join(lines)


def main(folder=HERE / "evidence", out=None):
    inventory = json.loads(INVENTORY.read_text())
    result = scan(load(folder), inventory)
    print(report(result))
    if out:
        out = pathlib.Path(out)
        out.mkdir(parents=True, exist_ok=True)
        for a in result["agents"]:
            if not a["known"]:
                name = slug(a["name"]) + ".json"
                (out / name).write_text(
                    json.dumps(draft(a), indent=2) + "\n")
                print("wrote", out / name)
    return result


if __name__ == "__main__":
    main(*sys.argv[1:3])
