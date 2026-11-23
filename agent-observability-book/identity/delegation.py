"""Delegation and consent for agents (Chapter 12).

Usage: python -m identity.delegation [OUT_DIR]

A small stand-in for an authorization server's token exchange
(RFC 8693). Speedy brings two tokens: the customer's (subject)
and its own workload identity (actor). The server checks the
agent's registered capabilities and the customer's consent, then
issues a short-lived token that names both: `sub` is the
customer, `act` is Speedy. The gateway checks all of it.
"""
import hashlib
import json
import pathlib
import sys

import jwt

from audit.keys import lab_key
from identity import workload as wl

AS = "https://auth.pronto.example"
LOGIN = "https://login.pronto.example"
CHAT = "chat.pronto.example"
GW = wl.GW
AS_KEY = lab_key("pronto-as-2027-02")
LOGIN_KEY = lab_key("pronto-login-2027-02")
NOW = wl.NOW + 120                # 2027-02-15 09:02 UTC
TTL = 300
VIA = "rfc8693_token_exchange"

SPEEDY = f"{wl.SPIFFE}/ns/support/agent/speedy"
CODER = f"{wl.SPIFFE}/ns/platform/agent/coder"

# what each agent may ever be delegated (registry, Chapter 11)
CAPABILITIES = {
    SPEEDY: {"orders:read:own", "refunds:create:max_50"},
    CODER: {"repo:write:platform"},
}
# what each customer agreed to, per agent
CONSENTS = {
    ("cust_7f3a91", SPEEDY): {
        "id": "cns_0193",
        "text": "Speedy may look up your orders and "
                "refund up to $50 per order",
        "scopes": {"orders:read:own",
                   "refunds:create:max_50"}},
    ("cust_2b8c04", SPEEDY): {
        "id": "cns_0207",
        "text": "Speedy may look up your orders",
        "scopes": {"orders:read:own"}},
}


def sign(claims, key, kid):
    return jwt.encode(claims, key, algorithm="EdDSA",
                      headers={"kid": kid})


def read(token, key, aud, iss, now):
    """Signature, issuer, audience and expiry, or a reason."""
    peek = jwt.decode(token,
                      options={"verify_signature": False})
    if aud not in peek.get("aud", []):
        return None, "wrong audience"
    try:
        c = jwt.decode(token, key.public_key(),
                       algorithms=["EdDSA"], audience=aud,
                       issuer=iss,
                       options={"verify_exp": False,
                                "verify_iat": False})
    except jwt.InvalidTokenError as e:
        return None, type(e).__name__
    if now >= c["exp"]:
        return None, "expired"
    return c, "ok"


def login(customer, now=NOW):
    """The customer's session token, issued to the chat app."""
    return sign({"iss": LOGIN, "sub": customer, "aud": [CHAT],
                 "tenant": "pronto", "iat": now,
                 "exp": now + 3600}, LOGIN_KEY, "login-2027-02")


def exchange(subject, actor, scopes, aud=GW, now=NOW):
    """RFC 8693: subject + actor token -> delegated token."""
    user, why = read(subject, LOGIN_KEY, CHAT, LOGIN, now)
    if not user:
        return None, f"subject token: {why}"
    if actor is None:
        return None, "no actor token"
    agent, why = wl.verify(actor, AS, now)
    if why != "ok":
        return None, f"actor token: {why}"
    asked = set(scopes)
    extra = asked - CAPABILITIES.get(agent, set())
    if extra:
        return None, "outside the agent's capabilities"
    consent = CONSENTS.get((user["sub"], agent))
    if not consent:
        return None, "no consent on record"
    if asked - consent["scopes"]:
        return None, "not consented: " + \
            " ".join(sorted(asked - consent["scopes"]))
    claims = {"iss": AS, "sub": user["sub"],
              "tenant": user["tenant"], "aud": [aud],
              "scope": " ".join(sorted(asked)),
              "act": {"sub": agent},
              "consent": consent["id"],
              "iat": now, "exp": now + TTL}
    return sign(claims, AS_KEY, "as-2027-02"), "issued"


def check(token, scope, owner=None, amount=None, now=NOW):
    """What the gateway checks before a delegated call."""
    c, why = read(token, AS_KEY, GW, AS, now)
    if not c:
        return why
    if "act" not in c:
        return "no acting agent named"
    if scope not in c["scope"].split():
        return "scope not delegated"
    if scope.endswith(":own") and owner != c["sub"]:
        return "not the principal's own"
    limit = scope.rpartition(":max_")[2]
    if amount is not None and limit.isdigit() \
            and amount > int(limit):
        return "over the delegated limit"
    return "ok"


def chain(claims, scopes):
    """The receipt's delegation_chain, outermost actor first."""
    out, act = [], claims.get("act")
    while act:
        out.append({"actor": act["sub"], "via": VIA,
                    "scopes": scopes})
        act = act.get("act")
    return out


def for_whom(token):
    """The receipt's for_whom, from the delegated token."""
    c = jwt.decode(token, options={"verify_signature": False})
    scopes = sorted(c["scope"].split())
    digest = hashlib.sha256(token.encode()).hexdigest()
    return {"principal_type": "user", "principal_id": c["sub"],
            "tenant_id": c["tenant"], "scopes": scopes,
            "delegation_chain": chain(c, scopes),
            "token_ref": f"sha256:{digest}"}


ASK = ["orders:read:own", "refunds:create:max_50"]
CODER_EVIDENCE = {"k8s:ns": "platform", "k8s:sa": "coder",
                  "image": "sha256:9a02…coder-3.1.0"}


def demo():
    rows = []
    session = login("cust_7f3a91")
    rows.append(("Customer signs in", "session token"))
    svid, why = wl.attest(wl.SPEEDY, AS)
    rows.append(("Speedy attests", why))
    token, why = exchange(session, svid, ASK)
    rows.append(("Exchange for the gateway", why))
    c = jwt.decode(token,
                   options={"verify_signature": False})
    rows.append((None, f"  sub    {c['sub']}"))
    rows.append((None, f"  act    {c['act']['sub']}"))
    rows.append((None, f"  scope  {c['scope']}"))
    rows.append(("$40 refund, cust_7f3a91",
                 check(token, "refunds:create:max_50",
                       amount=40)))
    rows.append(("$85 refund",
                 check(token, "refunds:create:max_50",
                       amount=85)))
    rows.append(("Orders of cust_2b8c04",
                 check(token, "orders:read:own",
                       owner="cust_2b8c04")))
    rows.append(("Session token passed on",
                 check(session, "refunds:create:max_50",
                       amount=40)))
    rows.append(("Same token, 6 min later",
                 check(token, "refunds:create:max_50",
                       amount=40, now=NOW + 360)))
    rows.append(("Speedy asks for max_500",
                 exchange(session, svid,
                          ["refunds:create:max_500"])[1]))
    rows.append(("Night Owl, no identity",
                 exchange(session, None, ASK)[1]))
    other = login("cust_2b8c04")
    rows.append(("cust_2b8c04, lookups only",
                 exchange(other, svid, ASK)[1]))
    coder, _ = wl.attest(CODER_EVIDENCE, AS)
    rows.append(("Coder asks to refund",
                 exchange(session, coder, ASK)[1]))
    saved = CONSENTS.pop(("cust_7f3a91", SPEEDY))
    rows.append(("Consent withdrawn",
                 exchange(session, svid, ASK)[1]))
    CONSENTS[("cust_7f3a91", SPEEDY)] = saved
    return token, rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    token, rows = demo()
    for label, result in rows:
        print(result if label is None
              else f"{label:<28}{result}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        claims = jwt.decode(token,
                            options={"verify_signature": False})
        (out / "speedy-delegated-claims.json").write_text(
            json.dumps(claims, indent=2) + "\n")
        (out / "for-whom.json").write_text(json.dumps(
            {"for_whom": for_whom(token)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
