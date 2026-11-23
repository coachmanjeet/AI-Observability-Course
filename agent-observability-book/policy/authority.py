"""Who authorized each refund, and what the payment checked
(Chapter 21).

Usage: python -m policy.authority

Three refunds, three sources of authority:
  $40   the customer's delegated scope, which stops at $50
  $85   a support lead's approval, bound to one order and one
        amount, valid for 15 minutes
  $120  an emergency grant from two leads (break-glass), with a
        ceiling and a 30-minute expiry
The gateway decides each one with Cedar. Then the payment
service checks the authority again, on the token the gateway
issued, because a decision made at 14:05 is only good for the
refund it named and only for as long as its authority lasts.
"""
from datetime import datetime, timezone

from policy import breakglass as bg
from policy import gateway as gw
from policy import oversight as ov
from pronto.payments import Payments, token

T0 = int(datetime(2027, 3, 9, 14, 5,
                  tzinfo=timezone.utc).timestamp())
gw.ORDERS.setdefault("ord_5655", "cust_7f3a91")


def hhmm(t):
    at = datetime.fromtimestamp(t, timezone.utc)
    return at.strftime("%H:%M")


def cases():
    """(label, authority line, gateway result, token, at)."""
    claims = gw.speedy_token()
    out = []

    call = gw.refund("ord_5521", "40.00")
    d = gw.decide(gw.request_from(call, claims),
                  claims["scope"].split())
    basis = {"kind": "delegated",
             "scope": "refunds:create:max_50"}
    raw = token(call, basis, "op_1", T0)
    out.append(("$40 ord_5521", "customer's delegated scope, "
                "max $50", d, raw, T0))

    call = gw.refund("ord_5602", "85.00")
    facts = {"amount": "85.00", "photo": True, "refunds_30d": 0}
    approval, _ = ov.approve("ord_5602", "85.00", facts,
                             "user:lead-ana")
    d = ov.refund_with("ord_5602", "85.00", approval)
    basis = {"kind": "approval", "id": "apr_01",
             "order": "ord_5602", "amount": "85.00",
             "expires": T0 + 15 * 60}
    line = f"apr_01, lead-ana, $85.00, to {hhmm(T0 + 900)}"
    raw = token(call, basis, "op_2", T0)
    out.append(("$85 ord_5602", line, d, raw, T0))
    no = dict(basis, kind="delegated")
    out.append(("$85, token without approval", None, None,
                token(call, no, "op_3", T0), T0))
    late = T0 + 20 * 60
    raw = token(call, basis, "op_4", late)
    out.append((f"$85, approval presented at {hhmm(late)}",
                None, None, raw, late))

    call = gw.refund("ord_5655", "120.00")
    grant, _ = bg.invoke("user:lead-ana", "user:lead-raj",
                         "approval service down", 150)
    decision, why = bg.decide(call, claims, grant)
    basis = {"kind": "break-glass", "id": "bg_01",
             "max": "150.00", "expires": T0 + 30 * 60}
    out.append(("$120 ord_5655", "bg_01, two leads, max $150, "
                f"to {hhmm(T0 + 1800)}",
                {"decision": decision,
                 "determining_policies": [why]},
                token(call, basis, "op_5", T0), T0))
    return out


def run():
    pay, rows = Payments(), []
    for label, line, d, raw, at in cases():
        rows.append((label, line, d, pay.pay(raw, at)))
    return rows, pay


def main():
    rows, pay = run()
    print("Who authorized each refund, Mar 9, 2027")
    for label, line, d, (status, what) in rows:
        print(f"  {label}")
        if line:
            print(f"    authority  {line}")
        if d:
            short = d["decision"].split("_")[0]
            print(f"    gateway    {short:<7}"
                  f"{d['determining_policies'][0]}")
        print(f"    payment    {status:<7}{what}")
    print(f"Ledger: {len(pay.ledger)} payments, each with its "
          f"basis")
    for e in pay.ledger:
        print(f"  {e['payment_id']}  {e['order']}  "
              f"${e['amount']:>6}  {e['basis']:<12}"
              f"{e['basis_id'] or ''}")


if __name__ == "__main__":
    main()
