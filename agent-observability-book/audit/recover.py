"""When the money moved and the receipt didn't (Chapter 8).

Usage: python -m audit.recover

One night, the receipt writer is down from 03:08 to 03:16. The
payment service keeps working, so payments land with no receipt
behind them. This lab starts from an empty record and does what
the on-call engineer does:

1. reconcile the payment ledger against receipts by operation
   key, and tell three different problems apart: a duplicate
   receipt (one payment, two records), a duplicate payment (two
   payments for one order) and a missing receipt
2. pause consequential writes when too many payments go
   unreceipted, because evidence is part of the control
3. rebuild each missing receipt from the witnesses that did see
   the action, mark every section with where it came from, and
   say what stays unknown
"""

from datetime import datetime, timedelta, timezone

from policy import gateway as gw
from pronto.payments import Payments, token

T0 = datetime(2027, 3, 16, 3, 0, tzinfo=timezone.utc)
PAUSE_AFTER = 3  # unreceipted payments before writes pause
OWNER = "platform on-call (receipt writer)"


def ts(minutes):
    return int((T0 + timedelta(minutes=minutes)).timestamp())


def night():
    """Payments, receipts and decisions, as they landed."""
    pay, receipts, decisions = Payments(), [], {}
    retries = []
    events = [  # minute, order, amount, op, receipt written?
        (2, "ord_5534", "22.00", "op_a1", 1),
        (9, "ord_5521", "40.00", "op_a2", 0),  # writer down
        (9, "ord_5521", "40.00", "op_a2", 0),  # agent retries
        (12, "ord_5530", "45.00", "op_a3", 0),
        (15, "ord_5602", "18.00", "op_a4", 0),
        (21, "ord_5640", "30.00", "op_a5", 2),  # writer back,
        # client resends
        (
            26,
            "ord_5640",
            "30.00",
            "op_a6",
            1,
        ),  # a second decision
    ]
    claims = gw.speedy_token()
    for minute, order, amount, op, written in events:
        call = gw.refund(order, amount)
        basis = {"kind": "delegated"}
        decisions[op] = {
            "op": op,
            "at": minute,
            "subject": claims["sub"],
            "on_behalf_of": (
                claims["act"]["sub"]
                if "act" in claims
                else "cust_7f3a91"
            ),
            "policy": "refunds-under-50-sampled-review",
            "decision": "allow",
            "order": order,
            "region": "us-west-2",
        }
        status, pid = pay.pay(
            token(call, basis, op, ts(minute)), ts(minute)
        )
        if status == "same":
            retries.append((minute, op, pid))
        for _ in range(written):
            receipts.append(
                {
                    "op": op,
                    "order": order,
                    "payment": pid,
                    "at": minute,
                }
            )
    return pay.ledger, receipts, decisions, retries


def reconcile(ledger, receipts):
    """One finding per payment, in ledger order."""
    by_op = {}
    for r in receipts:
        by_op.setdefault(r["op"], []).append(r)
    orders = {}
    for e in ledger:
        orders.setdefault(e["order"], []).append(e)
    out = []
    for e in ledger:
        n = len(by_op.get(e["op"], []))
        if (
            len(orders[e["order"]]) > 1
            and e is not orders[e["order"]][0]
        ):
            finding = "duplicate payment"
        elif n == 0:
            finding = "missing receipt"
        elif n > 1:
            finding = f"duplicate receipt ({n} for 1)"
        else:
            finding = "ok"
        out.append((e, finding))
    return out


def pause_at(findings):
    """Minute at which consequential writes pause, or None."""
    missing = 0
    for e, finding in findings:
        if finding == "missing receipt":
            missing += 1
            if missing >= PAUSE_AFTER:
                return (e["at"] - int(T0.timestamp())) // 60
    return None


def rebuild(entry, decision):
    """A receipt from the witnesses, each section marked."""
    return [
        ("who", "gateway decision", "witnessed"),
        ("for whom", "gateway decision", "witnessed"),
        ("under which rule", "gateway decision", "witnessed"),
        (
            "did what",
            f"ledger {entry['payment_id']}",
            "witnessed",
        ),
        ("where", "gateway region", "witnessed"),
        ("knowing what", "trace not kept", "unknown"),
        ("at what cost", "trace not kept", "unknown"),
    ]


def main():
    ledger, receipts, decisions, retries = night()
    findings = reconcile(ledger, receipts)
    print("Ledger against receipts, Mar 16, 2027, 03:00-03:30")
    for e, finding in findings:
        print(
            f"  {e['payment_id']}  {e['order']}  "
            f"${e['amount']:>5}  {finding}"
        )
    for minute, op, pid in retries:
        print(
            f"Retry of {op} at 03:{minute:02d}: same payment, "
            f"{pid}"
        )
    minute = pause_at(findings)
    print(
        f"Alert at 03:{minute:02d}: {PAUSE_AFTER} payments "
        f"without receipts"
    )
    print(f"  page {OWNER}")
    print(
        "  pause refunds at the gateway; writer back at 03:16"
    )
    missing = [e for e, f in findings if f == "missing receipt"]
    first = missing[0]
    print(
        f"Rebuilt receipt for {first['payment_id']} "
        f"({first['op']}), marked reconstructed"
    )
    for section, source, state in rebuild(
        first, decisions[first["op"]]
    ):
        print(f"  {section:<17}{source:<19}{state}")
    print("  conformance: R2 at most; two answers unknown")


if __name__ == "__main__":
    main()
