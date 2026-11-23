"""Workload identity for agents, the SPIFFE way (Chapter 16).

Usage: python -m identity.workload [OUT_DIR]

A small stand-in for a SPIRE server: agents prove what they are by
attestation (where they run, which image, which service account),
not by a secret they hold. A match against a registration entry,
for an agent the registry has approved, earns a short-lived JWT-SVID
for one audience. The gateway verifies it before every call.
"""
import json
import pathlib
import sys

import jwt

from audit.keys import lab_key

TRUST_DOMAIN = "pronto.example"
TTL = 300                         # seconds
NOW = 1_802_682_000               # 2027-02-15 09:00 UTC
SPIFFE = f"spiffe://{TRUST_DOMAIN}"
ISSUER = f"{SPIFFE}/spire/server"
KEY = lab_key("pronto-spire-2027-02")

# registration entries: selectors a workload must show to get an ID
ENTRIES = [
    {"spiffe_id": f"{SPIFFE}/ns/support/agent/speedy",
     "agent": "agent://pronto/speedy",
     "selectors": {"k8s:ns": "support", "k8s:sa": "speedy",
                   "image": "sha256:5e1f…speedy-2.3.1"}},
    {"spiffe_id": f"{SPIFFE}/ns/platform/agent/coder",
     "agent": "agent://pronto/coder",
     "selectors": {"k8s:ns": "platform", "k8s:sa": "coder",
                   "image": "sha256:9a02…coder-3.1.0"}},
    {"spiffe_id": f"{SPIFFE}/ns/warehouse/agent/tally",
     "agent": "agent://unregistered/tally",
     "selectors": {"k8s:ns": "warehouse", "k8s:sa": "tally",
                   "image": "sha256:77c4…tally-0.3.0"}},
]
APPROVED = {"agent://pronto/speedy", "agent://pronto/coder",
            "agent://unregistered/tally"}


def attest(evidence, audience, now=NOW):
    """An SVID for a workload whose evidence matches an entry."""
    for e in ENTRIES:
        if all(evidence.get(k) == v for k, v in e["selectors"].items()):
            if e["agent"] not in APPROVED:
                return None, "agent not approved in the registry"
            claims = {"sub": e["spiffe_id"], "aud": [audience],
                      "iss": ISSUER, "iat": now, "exp": now + TTL}
            token = jwt.encode(claims, KEY, algorithm="EdDSA",
                               headers={"kid": "spire-2027-02"})
            return token, "issued"
    return None, "no registration entry matches"


def verify(token, audience, now=NOW):
    """What a gateway checks before it accepts a call."""
    try:
        claims = jwt.decode(token, KEY.public_key(),
                            algorithms=["EdDSA"], audience=audience,
                            issuer=ISSUER,
                            options={"verify_exp": False,
                                     "verify_iat": False})
    except jwt.InvalidAudienceError:
        return None, "wrong audience"
    except jwt.InvalidTokenError as e:
        return None, type(e).__name__
    if now >= claims["exp"]:
        return None, "expired"
    if not claims["sub"].startswith(SPIFFE + "/"):
        return None, "foreign trust domain"
    return claims["sub"], "ok"


SPEEDY = {"k8s:ns": "support", "k8s:sa": "speedy",
          "image": "sha256:5e1f…speedy-2.3.1"}
LAPTOP = {"host": "analyst-laptop-0233", "user": "analyst-0233"}
GW = "mcp-gateway.pronto.example"


def demo():
    rows = []
    token, why = attest(SPEEDY, GW)
    rows.append(("Speedy in support/speedy", why))
    sub, ok = verify(token, GW)
    rows.append(("  gateway verifies", ok))
    rows.append((None, f"    {sub}"))
    rows.append(("  same token, payments API",
                 verify(token, "payments.pronto.example")[1]))
    rows.append(("  same token, 6 minutes later",
                 verify(token, GW, NOW + 360)[1]))
    forged = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")
    rows.append(("  one byte changed",
                 verify(forged, GW)[1]))
    rows.append(("Night Owl on a laptop",
                 attest(LAPTOP, GW)[1]))
    other = {**SPEEDY, "image": "sha256:0bad…speedy-patched"}
    rows.append(("Speedy from an unknown image", attest(other, GW)[1]))
    return token, rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    token, rows = demo()
    for label, result in rows:
        print(result if label is None else f"{label:<32}{result}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        claims = jwt.decode(token, options={"verify_signature": False})
        (out / "speedy-svid-claims.json").write_text(
            json.dumps(claims, indent=2) + "\n")
        # attested here, so the receipt says verified (Appendix A)
        who = {"workload_id": claims["sub"], "identity": "verified"}
        (out / "who-workload.json").write_text(json.dumps(
            {"who": who}, indent=2) + "\n")


if __name__ == "__main__":
    main()
