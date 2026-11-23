"""Make the gateway the only path (Chapter 14).

Usage: python -m policy.boundary

A gateway only governs the calls that cross it. This lab adds
the three properties that make it the only path:

1. The refund service accepts a call only with a token the
   gateway issued for that exact request, so a direct call, or
   a gateway token replayed for another request, is rejected.
2. When the decision engine can't be reached, consequential
   calls fail closed. Calls that aren't consequential pass.
3. Decisions are cached briefly, keyed by the policy set's
   digest and the freeze switch, so a policy change or a
   freeze invalidates every cached allow.
"""
import hashlib
import json

import jwt

from audit.keys import lab_key
from policy import gateway as gw
from pronto.tools import refunds_create
from pronto.world import World

GW_KEY = lab_key("pronto-gateway-2027-02")
SERVICE = "svc://pronto/refunds"
NOW = 1772013600            # Feb 25, 2027, 10:00 UTC
TTL = 60                    # seconds a decision is cached
CONSEQUENTIAL = {"refunds.create": "financial",
                 "orders.get": "read_sensitive",
                 "cases.escalate": "write"}


def _digest(call):
    raw = json.dumps(call, sort_keys=True).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def gateway_token(call, now=NOW):
    """Issued by the gateway after an allow, for one request."""
    return jwt.encode({"iss": gw.EP, "aud": SERVICE,
                       "req": _digest(call), "iat": now,
                       "exp": now + 30}, GW_KEY,
                      algorithm="EdDSA")


class RefundService:
    """The system of record: it trusts only the gateway."""

    def __init__(self):
        self.world = World(refund_seq=8101)
        self.public = GW_KEY.public_key()

    def call(self, call, token, now=NOW):
        try:
            claims = jwt.decode(token, self.public,
                                algorithms=["EdDSA"],
                                audience=SERVICE,
                                options={"verify_iat": False},
                                leeway=10**9)
        except jwt.InvalidTokenError:
            return "reject", "not issued by the gateway"
        if claims["exp"] < now:
            return "reject", "gateway token expired"
        if claims["req"] != _digest(call):
            return "reject", "bound to another request"
        out = refunds_create(self.world, call["arguments"])
        return "allow", out["ref"]


class Gateway:
    """Decides, caches briefly, fails closed, then forwards."""

    def __init__(self, policies=(gw.POLICY, "3")):
        self.policies, self.cache = policies, {}
        self.pdp_up, self.freeze = True, False

    def decide(self, call, claims, now=NOW):
        if call["tool"] not in CONSEQUENTIAL:
            return "allow", "not consequential"
        ref = gw.policy_set(*self.policies)[2]
        key = (ref["digest"], self.freeze, _digest(call))
        hit = self.cache.get(key)
        if hit and now - hit[0] < TTL:
            return hit[1], "cached"
        stale = any(k[2] == key[2] for k in self.cache)
        why = "decided again" if stale else "decided"
        if not self.pdp_up:
            return "deny", "fail closed"
        req = gw.request_from(call, claims)
        scopes = claims["scope"].split()
        d = gw.decide(req, scopes, freeze=self.freeze,
                      policies=self.policies)
        self.cache[key] = (now, d["decision"])
        return d["decision"], why


def read(order):
    return {"tool": "orders.get",
            "arguments": {"order_id": order, "amount": "0.00",
                          "currency": "USD"}}


def run():
    """Every row: (label, outcome, why)."""
    rows = []
    claims = gw.speedy_token()
    svc, gate = RefundService(), Gateway()
    call = gw.refund("ord_5521", "40.00")

    decision, _ = gate.decide(call, claims)
    assert decision == "allow"
    token = gateway_token(call)
    rows.append(("via gateway, $40", *svc.call(call, token)))
    speedy = jwt.encode({"sub": claims["sub"], "aud": SERVICE},
                        lab_key("speedy-delegated"),
                        algorithm="EdDSA")
    rows.append(("direct, Speedy's own token",
                 *svc.call(call, speedy)))
    other = gw.refund("ord_5530", "40.00")
    rows.append(("gateway token, other order",
                 *svc.call(other, token)))

    gate.pdp_up = False
    gate.cache.clear()
    search = {"tool": "catalog.search", "arguments": {}}
    for label, c in (("refund $40", call),
                     ("orders.get", read("ord_5521")),
                     ("catalog.search", search)):
        rows.append((f"engine down, {label}",
                     *gate.decide(c, claims)))

    gate.pdp_up = True
    gate.decide(call, claims)
    rows.append(("same call 20 s later",
                 *gate.decide(call, claims, now=NOW + 20)))
    gate.freeze = True
    rows.append(("payments freeze on",
                 *gate.decide(call, claims, now=NOW + 22)))
    gate.freeze = False
    gate.policies = (gw.HERE / "pronto-refunds-v4.cedar", "4")
    rows.append(("after policy v3 -> v4",
                 *gate.decide(call, claims, now=NOW + 25)))
    return rows


def main():
    print("The only path: Feb 25, 2027")
    for label, outcome, why in run():
        print(f"  {label:<28}{outcome:<8}{why}")


if __name__ == "__main__":
    main()
