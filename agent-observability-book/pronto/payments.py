"""Pronto's payment service: the system of record for refunds.

Used by Chapter 21 (who authorized a refund) and Chapter 8 (a
payment whose receipt never arrived). It trusts the gateway and
nothing else, and it checks two things the gateway's decision
alone can't guarantee by the time the call arrives:

- the authority: a refund over $50 must carry an approval bound
  to this order and amount, or an emergency grant, unexpired
- the operation key: a retry with the same key returns the same
  payment, so a lost response never becomes a second refund

Its ledger is the independent witness. A receipt can go missing;
the ledger entry can't.
"""
from decimal import Decimal

import jwt

from audit.keys import lab_key

GW_KEY = lab_key("pronto-gateway-2027-02")
SERVICE = "svc://pronto/payments"
GATEWAY = "gateway://pronto/mcp-gateway-us-west"
CHECKS = {"verify_exp": False, "verify_iat": False,
          "verify_nbf": False}   # checked against `now` below
LIMIT = Decimal("50.00")     # the customer's delegated ceiling


def token(call, basis, op, iat):
    """What the gateway issues after an allow."""
    args = call["arguments"]
    claims = {"iss": GATEWAY, "aud": SERVICE, "op": op,
              "iat": iat, "exp": iat + 30,
              "order": args["order_id"],
              "amount": args["amount"], "basis": basis}
    return jwt.encode(claims, GW_KEY, algorithm="EdDSA")


def authority(claims, now):
    """None if the basis covers the amount, else the reason."""
    amount, basis = Decimal(claims["amount"]), claims["basis"]
    if amount <= LIMIT and basis["kind"] == "delegated":
        return None
    if basis["kind"] == "approval":
        if (basis["order"], basis["amount"]) != \
                (claims["order"], claims["amount"]):
            return "approval is for another refund"
        if now >= basis["expires"]:
            return f"approval {basis['id']} expired"
        return None
    if basis["kind"] == "break-glass":
        if amount > Decimal(basis["max"]):
            return f"above the grant's ${basis['max']}"
        if now >= basis["expires"]:
            return f"grant {basis['id']} expired"
        return None
    return "above $50 needs an approval or grant"


class Payments:
    def __init__(self):
        self.ledger = []          # the independent record

    def pay(self, raw, now):
        try:
            claims = jwt.decode(raw, GW_KEY.public_key(),
                                algorithms=["EdDSA"],
                                audience=SERVICE,
                                options=CHECKS)
        except jwt.InvalidTokenError:
            return "reject", "not issued by the gateway"
        if claims["exp"] < now:
            return "reject", "gateway token expired"
        for entry in self.ledger:
            if entry["op"] == claims["op"]:
                return "same", entry["payment_id"]
        why = authority(claims, now)
        if why:
            return "reject", why
        pid = f"pay_{len(self.ledger) + 1:04d}"
        basis = claims["basis"]
        self.ledger.append({"payment_id": pid,
                            "op": claims["op"],
                            "order": claims["order"],
                            "amount": claims["amount"],
                            "basis": basis["kind"],
                            "basis_id": basis.get("id"),
                            "at": now})
        return "paid", pid
