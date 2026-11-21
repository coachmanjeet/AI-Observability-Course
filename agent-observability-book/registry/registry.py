"""One registry for every agent and MCP server (Chapter 15).

Usage: python -m registry.registry OUT_DIR

Builds Pronto's registry from three inputs: the inventory, the
drafts discovery found (Chapter 14), and what third parties publish
about themselves (an A2A agent card, an MCP server record). Each
record gets an owner, a version, capabilities and a risk tier, and
moves through a lifecycle only by recorded decisions.
"""
import json
import pathlib
import sys

from registry.discover import HERE as REG, INVENTORY, load, scan

STATES = ["draft", "in_review", "approved", "deprecated", "retired"]
MOVES = {("draft", "in_review"), ("in_review", "approved"),
         ("in_review", "retired"), ("draft", "retired"),
         ("approved", "deprecated"), ("deprecated", "retired"),
         ("approved", "retired")}
HIGH = {"financial", "destructive", "permission_change"}
MEDIUM = {"write", "external_communication", "read_sensitive"}
VERSIONS = {"agent://pronto/speedy": "2.3.1",
            "agent://pronto/pick": "1.8.0",
            "agent://pronto/route": "0.9.4",
            "agent://pronto/coder": "3.1.0"}


def tier(effects):
    """Risk tier from the consequence classes an agent can cause."""
    if HIGH & set(effects):
        return "high"
    return "medium" if MEDIUM & set(effects) else "low"


def ref(rec):
    name = rec["id"].rsplit("/", 1)[1]
    return f"registry://pronto/agents/{name}@{rec['version']}"


class Registry:
    def __init__(self):
        self.records, self.events = {}, []

    def put(self, rec):
        self.records[rec["id"]] = rec

    def move(self, rid, to, by, reason, on):
        """Change state only by a decision, and keep the decision."""
        rec = self.records[rid]
        if (rec["state"], to) not in MOVES:
            raise ValueError(f"{rec['state']} -> {to} not allowed")
        if to == "approved":
            missing = [k for k in ("owner", "version")
                       if not rec.get(k) or rec[k] == "unknown"]
            if rec["risk_tier"] == "high" and \
                    not rec.get("security_review"):
                missing.append("security_review")
            if missing:
                raise ValueError("cannot approve without "
                                 + ", ".join(missing))
        self.events.append({"record": rid, "from": rec["state"],
                            "to": to, "by": by, "reason": reason,
                            "on": on})
        rec["state"] = to

    def who(self, rid, runtime):
        """The receipt's who section, from the registry."""
        rec = self.records[rid]
        return {"agent_id": rec["id"], "agent_name": rec["name"],
                "agent_version": rec["version"],
                "kind": rec["kind"], "owner": rec["owner"],
                "registry_ref": ref(rec), "runtime": runtime}


def from_card(card, owner):
    """A third party's own A2A agent card, as a record."""
    org = card["provider"]["organization"].lower()
    return {"id": f"agent://{org}/{card['name'].lower()}",
            "name": card["name"], "version": card["version"],
            "kind": "third_party", "owner": owner,
            "capabilities": [s["id"] for s in card["skills"]],
            "source": "a2a agent card"}


def build():
    """Pronto's registry as of Feb 8, 2027."""
    reg = Registry()
    inventory = json.loads(INVENTORY.read_text())
    found = scan(load(REG / "evidence"), inventory)
    effects = {a["agent_id"]: a["effects"] for a in found["agents"]}
    kinds = {"1P": "first_party", "3P": "third_party",
             "shadow": "shadow"}
    for a in inventory["agents"]:
        rec = {"id": a["agent_id"], "name": a["name"],
               "version": VERSIONS.get(a["agent_id"], "unknown"),
               "kind": kinds[a["kind"]], "owner": a.get("owner"),
               "source": "inventory",
               "effects": effects.get(a["agent_id"], [])}
        reg.put(rec)
    card = json.loads((REG / "cards/ledger.agent-card.json")
                      .read_text())
    reg.records["agent://payco/ledger"].update(
        from_card(card, "team:finance"))
    server = json.loads((REG / "cards/promo.server.json")
                        .read_text())
    reg.records["agent://campaignly/promo"].update(
        version=server["version"], capabilities=server["tools"],
        source="mcp server record")
    for a in found["agents"]:
        if not a["known"]:
            reach = ["read_sensitive"] if a["mcp_servers"] else []
            reg.put({"id": a["agent_id"], "name": a["name"],
                     "version": "unknown", "kind": a["kind"],
                     "owner": None, "source": "discovery",
                     "effects": a["effects"] + reach})
    for rec in reg.records.values():
        rec["risk_tier"] = tier(rec.get("effects", []))
        rec["state"] = "approved" if rec["source"] != "discovery" \
            and rec["kind"] != "shadow" else "draft"
        rec["security_review"] = rec["state"] == "approved"
    return reg


def review_week(reg):
    """The first weekly review: three decisions."""
    tally = "agent://unregistered/tally"
    reg.move(tally, "in_review", "warehouse ops lead",
             "claimed; reconciles stock counts", "2027-02-08")
    reg.records[tally].update(owner="team:warehouse-ops",
                              version="0.3.0", kind="first_party")
    reg.move(tally, "approved", "platform lead",
             "medium tier; must get its own credential",
             "2027-02-08")
    ide = "agent://unregistered/ide-assistant"
    reg.move(ide, "retired", "security lead",
             "unclaimed; pg-prod removed from the laptop",
             "2027-02-08")
    owl = "agent://unregistered/night-owl"
    reg.move(owl, "retired", "platform lead",
             "laptop agent stopped and wiped", "2027-02-08")


def report(reg):
    lines = [f"{'agent':<14}{'kind':<12}{'tier':<8}{'state':<9}"
             "owner"]
    for rec in reg.records.values():
        lines.append(f"{rec['name']:<14}{rec['kind']:<12}"
                     f"{rec['risk_tier']:<8}{rec['state']:<9}"
                     f"{rec['owner'] or '-'}")
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    reg = build()
    review_week(reg)
    print(report(reg))
    print()
    for e in reg.events:
        print(f"{e['on']}  {e['record'].rsplit('/', 1)[1]:<14}"
              f"{e['from']} -> {e['to']}")
        print(f"  {e['by']}: {e['reason']}")
    reg.put({**reg.records["agent://pronto/speedy"],
             "version": "2.4.0", "state": "in_review",
             "security_review": False,
             "id": "agent://pronto/speedy-2.4.0"})
    try:
        reg.move("agent://pronto/speedy-2.4.0", "approved",
                 "support lead", "new version", "2027-02-08")
    except ValueError as e:
        print(f"\napprove Speedy 2.4.0: refused\n  {e}")
    who = reg.who("agent://pronto/speedy", "pronto-support-runtime")
    print(f"\nreceipt who.registry_ref: {who['registry_ref']}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "who-speedy.json").write_text(
            json.dumps({"who": who}, indent=2) + "\n")
        (out / "registry.json").write_text(json.dumps(
            {"records": list(reg.records.values()),
             "events": reg.events}, indent=2) + "\n")


if __name__ == "__main__":
    main()
