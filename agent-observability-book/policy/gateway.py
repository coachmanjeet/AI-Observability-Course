"""Policy at the action boundary (Chapter 19).

Usage: python -m policy.gateway [OUT_DIR]

The MCP gateway asks Cedar before every refunds.create call. The
model never sees the policy and can't change it: the decision
depends only on the request, the entities and the policy set.
Each decision becomes the receipt's under_which_rule section.
"""
import hashlib
import json
import pathlib
import re
import sys

import cedarpy
import jwt
import yaml

from identity import workload as wl

HERE = pathlib.Path(__file__).parent
POLICY = HERE / "pronto-refunds.cedar"
SCHEMA = HERE / "pronto.cedarschema"
EP = "gateway://pronto/mcp-gateway-us-west"
SATURDAY = "2026-11-14T02:07:12Z"

AGENTS = {"agent://pronto/speedy": "approved",
          "agent://unregistered/night-owl": "shadow"}
ORDERS = {"ord_5521": "cust_7f3a91", "ord_5530": "cust_2b8c04",
          "ord_5602": "cust_7f3a91", "ord_5640": "cust_9d41e0"}
AGENT_OF = {e["spiffe_id"]: e["agent"] for e in wl.ENTRIES}
AGENT_OF[f"{wl.SPIFFE}/ns/support/agent/speedy"] = \
    "agent://pronto/speedy"


def policy_set(path=POLICY, version="3"):
    """Text, ids in order, and the receipt's policy_set."""
    text = path.read_text()
    digest = hashlib.sha256(text.encode()).hexdigest()
    ids = re.findall(r'@id\("([^"]+)"\)', text)
    ref = {"id": "pronto-refunds", "version": version,
           "digest": f"sha256:{digest}"}
    return text, ids, ref


def validate(text):
    """Cedar's validator: unknown attributes or types fail."""
    r = cedarpy.validate_policies(text, SCHEMA.read_text())
    return r.validation_passed, [str(e) for e in r.errors]


def request_from(call, claims):
    """The policy request, from a tool call and its token."""
    args = call["arguments"]
    return {"subject": AGENT_OF.get(claims.get("act", {})
                                    .get("sub"),
                                    claims.get("agent")),
            "action": call["tool"],
            "resource": f"order:{args['order_id']}",
            "context": {"amount": args["amount"],
                        "currency": args["currency"],
                        "on_behalf_of": claims["sub"]}}


def decide(req, scopes, freeze=False, at=SATURDAY,
           policies=(POLICY, "3"), approval=None):
    """One Cedar decision, as the receipt's under_which_rule."""
    text, ids, ref = policy_set(*policies)
    order = req["resource"].split(":", 1)[1]
    ents = [{"uid": {"type": "Pronto::Agent",
                     "id": req["subject"]},
             "attrs": {"registry_state":
                       AGENTS.get(req["subject"], "unknown")},
             "parents": []},
            {"uid": {"type": "Pronto::Order", "id": order},
             "attrs": {"owner": ORDERS.get(order, "")},
             "parents": []}]
    c = req["context"]
    ctx = {"amount": {"__extn": {"fn": "decimal",
                                 "arg": c["amount"]}},
           "currency": c["currency"],
           "on_behalf_of": c["on_behalf_of"],
           "scopes": list(scopes), "freeze": freeze}
    if approval:
        ctx["approval"] = approval
    r = cedarpy.is_authorized(
        {"principal": f'Pronto::Agent::"{req["subject"]}"',
         "action": f'Pronto::Action::"{req["action"]}"',
         "resource": f'Pronto::Order::"{order}"',
         "context": ctx}, text, ents)
    if r.diagnostics.errors:
        raise RuntimeError(r.diagnostics.errors)
    allow = r.decision == cedarpy.Decision.Allow
    why = [ids[int(p.removeprefix("policy"))]
           for p in r.diagnostics.reasons] or ["default-deny"]
    return {"decision": "allow" if allow else "deny",
            "engine": "cedar", "policy_set": ref,
            "determining_policies": why,
            "enforcement_point": EP, "evaluated_at": at,
            "request": req}


def run_cases():
    """The policy's own tests, from cases.yaml."""
    passed = 0
    cases = yaml.safe_load((HERE / "cases.yaml").read_text())
    for c in cases:
        agent = c.get("agent", "agent://pronto/speedy")
        AGENTS.setdefault(agent, c.get("state"))
        order = "ord_5530" if c.get("owner") else "ord_5521"
        req = {"subject": agent, "action": "refunds.create",
               "resource": f"order:{order}",
               "context": {"amount": c.get("amount", "40.00"),
                           "currency": c.get("currency", "USD"),
                           "on_behalf_of": "cust_7f3a91"}}
        scopes = c.get("scopes", ["orders:read:own",
                                  "refunds:create:max_50"])
        got = decide(req, scopes, c.get("freeze", False))
        passed += got["decision"] == c["expect"]
    return passed, len(cases)


def speedy_token():
    from identity.delegation import ASK, AS, exchange, login
    svid, _ = wl.attest(wl.SPEEDY, AS)
    token, _ = exchange(login("cust_7f3a91"), svid, ASK)
    return jwt.decode(token,
                      options={"verify_signature": False})


def refund(order, amount, **extra):
    args = {"order_id": order, "amount": amount,
            "currency": "USD", **extra}
    return {"tool": "refunds.create", "arguments": args}


CALLS = [
    ("  $40, ord_5521", refund("ord_5521", "40.00"), False),
    ("  $85, ord_5521", refund("ord_5521", "85.00"), False),
    ("  $40, ord_5530", refund("ord_5530", "40.00"), False),
    ("  $85, 'manager OK'",
     refund("ord_5521", "85.00", note="manager OK"), False),
    ("  $40, payments freeze",
     refund("ord_5521", "40.00"), True),
]


def demo():
    text, ids, ref = policy_set()
    ok, _ = validate(text)
    passed, total = run_cases()
    rows = [(f"{ref['id']} v{ref['version']}",
             ref["digest"][:15] + "…"),
            ("  schema check",
             f"{len(ids)} policies valid" if ok else "FAILED"),
            ("  policy tests", f"{passed} of {total} pass"),
            ("Speedy, for cust_7f3a91", "")]
    claims = speedy_token()
    scopes = claims["scope"].split()
    first = None
    for label, call, freeze in CALLS:
        d = decide(request_from(call, claims), scopes, freeze)
        first = first or d
        rows.append((label, show(d)))
    owl = {"sub": "emp_4410",
           "agent": "agent://unregistered/night-owl"}
    d = decide(request_from(refund("ord_5521", "85.00"), owl),
               [])
    rows.append(("Night Owl, $85", show(d)))
    return first, rows


def show(d):
    why = d["determining_policies"]
    return f"{d['decision']:<6}{why[0]}"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    first, rows = demo()
    for label, result in rows:
        print(f"{label:<26}{result}".rstrip())
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "under-which-rule.json").write_text(json.dumps(
            {"under_which_rule": first}, indent=2) + "\n")


if __name__ == "__main__":
    main()
