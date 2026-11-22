"""Break-glass and in-flight revocation (Chapter 21).

Usage: python -m policy.breakglass

Break-glass is an override for an emergency, and it is also an
attack path, so it gets the same treatment as any permission:
  - two people: the invoker can't approve their own grant
  - a scope: one action, an amount ceiling, a reason
  - an expiry: 30 minutes, then the normal policy is back
  - only a permit: Cedar's forbids still win, so a pause, a
    freeze or an unregistered agent still means deny, and the
    order still has to belong to the customer
  - a review: every action under the grant is listed at expiry

Revocation is the other half. A call authorized before the
agent was revoked must not run after it, so the system of record
checks the agent's revocation time, not only the token's expiry.
"""
import pathlib
from datetime import datetime, timedelta

import jwt

from policy import boundary as bd
from policy import gateway as gw

AT = datetime(2027, 3, 9, 14, 0)


def invoke(invoker, approver, reason, max_amount, at=AT):
    """A grant, or the reason it was refused."""
    if invoker == approver:
        return None, "needs a second person"
    if not reason:
        return None, "needs a reason"
    return {"id": "bg_01", "invoker": invoker,
            "approver": approver, "reason": reason,
            "action": "refunds.create", "max": max_amount,
            "expires": at + timedelta(minutes=30),
            "used": []}, "granted"


GRANT = """
@id("break-glass-{id}")
permit (
  principal == Pronto::Agent::"agent://pronto/speedy",
  action == Pronto::Action::"refunds.create",
  resource is Pronto::Order
)
when {{
  context.amount.lessThanOrEqual(decimal("{max}.00")) &&
  context.currency == "USD" &&
  resource.owner == context.on_behalf_of
}};
"""
ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "build" / "breakglass"


def policies(grant, at):
    """The base set, plus the grant's permit while it lasts."""
    text = gw.POLICY.read_text()
    version = "3"
    if grant and at < grant["expires"]:
        text += GRANT.format(**grant)
        version = f"3+{grant['id']}"
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"policy-{version}.cedar"
    path.write_text(text)
    return path, version


def decide(call, claims, grant=None, freeze=False, at=AT):
    """Cedar decides. A grant only adds a permit, so every
    forbid, the owner check and the expiry still hold."""
    req = gw.request_from(call, claims)
    d = gw.decide(req, claims["scope"].split(), freeze=freeze,
                  policies=policies(grant, at))
    why = d["determining_policies"][0]
    if grant and why.startswith("break-glass"):
        grant["used"].append((at, call["arguments"]["amount"]))
    return d["decision"], why


class Service(bd.RefundService):
    """The refund service, now checking revocations too."""

    def __init__(self):
        super().__init__()
        self.revoked = {}       # agent -> time it was revoked

    def call(self, call, token, now=bd.NOW):
        claims = jwt.decode(token, options={
            "verify_signature": False})
        cut = self.revoked.get(claims.get("agent"))
        if cut is not None and claims["iat"] < cut:
            return "reject", "revoked after authorization"
        return super().call(call, token, now)


def token_for(call, agent, iat):
    return jwt.encode({"iss": gw.EP, "aud": bd.SERVICE,
                       "agent": agent, "req": bd._digest(call),
                       "iat": iat, "exp": iat + 30},
                      bd.GW_KEY, algorithm="EdDSA")


def run():
    rows = []
    claims = gw.speedy_token()
    _, why = invoke("user:lead-ana", "user:lead-ana",
                    "approvals down", 150)
    rows.append(("self-approved grant", "refused", why))
    grant, why = invoke("user:lead-ana", "user:lead-raj",
                        "approval service down", 150)
    rows.append(("grant, second lead", why,
                 "30 min, refunds up to $150"))
    for label, amount, freeze, at in (
            ("$120 under the grant", "120.00", False, AT),
            ("$180 under the grant", "180.00", False, AT),
            ("$120, another customer", "120.00", False, AT),
            ("$120, payments freeze", "120.00", True, AT),
            ("$120 after expiry", "120.00", False,
             AT + timedelta(minutes=31))):
        order = "ord_5640" if "another" in label else "ord_5602"
        call = gw.refund(order, amount)
        rows.append((label, *decide(call, claims, grant,
                                    freeze, at)))
    rows.append(("review at expiry", "listed",
                 f"{len(grant['used'])} action under bg_01"))

    svc, speedy = Service(), "agent://pronto/speedy"
    call = gw.refund("ord_5521", "40.00")
    t0 = bd.NOW
    rows.append(("authorized, then run",
                 *svc.call(call, token_for(call, speedy, t0),
                           now=t0 + 10)))
    svc.revoked[speedy] = t0 + 5
    rows.append(("revoked before it ran",
                 *svc.call(call, token_for(call, speedy, t0),
                           now=t0 + 10)))
    return rows


def main():
    print("Break-glass and revocation, Mar 9, 2027")
    for label, outcome, why in run():
        print(f"  {label:<24}{outcome:<9}{why}")


if __name__ == "__main__":
    main()
