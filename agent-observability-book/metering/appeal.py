"""One appealed refund, from denial to the next release (Ch 27).

Usage: python -m metering.appeal

A Hilltop customer sends a photo of damaged salmon. Speedy
measures the photo window from the scheduled delivery time, not
the actual one, and declines a valid claim. The customer goes
quiet, so the seven-day outcome says "achieved" and Hilltop is
billed for a resolution. Two weeks later the customer appeals.

The lab follows the correction through every record it touches,
without editing any of them: a refund paid on a bound approval,
an outcome record that supersedes the first one, a credit under
the same idempotency key, and a new eval case. Then it counts
how many of February's silent declines the metric called a
success, which is the PM's reason to change the metric.
"""

from datetime import datetime, timedelta, timezone

from metering.traffic import (
    MONDAY_POLICY,
    day,
    first_time,
    month,
)
from metering.value import by_conversation, outcomes
from policy import gateway as gw
from pronto.payments import Payments, token
from receipts.tools import GENESIS, record_hash, seal

TENANT = "tenant:hilltop"
CASE = "conv_2558909d"
LATE_H = 9  # the van arrived 9 hours late
PRICE = "0.40"  # Hilltop's pilot price, per resolution
CLOSE = datetime(2027, 2, 28, 23, 59, tzinfo=timezone.utc)
APPEAL = datetime(2027, 3, 8, 10, 2, tzinfo=timezone.utc)
UPHELD = APPEAL + timedelta(minutes=38)
WINDOW = MONDAY_POLICY["photo_window_hours"]


def ts(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def february():
    spans, convs = month(TENANT, day("2027-02-01"), 28)
    per = by_conversation(spans)
    rows = {
        r["conversation_id"]: r for r in outcomes(convs, per)
    }
    firsts = [c for c in convs if not c["follow_up"]]
    declined = [
        c
        for c in firsts
        if first_time(c, WINDOW, 5000) == "declined"
    ]
    quiet = [
        c
        for c in declined
        if rows[c["conversation_id"]]["status"] == "achieved"
    ]
    billed_feb = [
        c
        for c in quiet
        if rows[c["conversation_id"]]["due"] <= CLOSE
    ]
    case = next(
        c for c in quiet if c["conversation_id"] == CASE
    )
    return declined, quiet, billed_feb, case, rows[CASE]


def chain(case, row):
    """Receipt, first outcome, superseding outcome: appended."""
    key = f"{CASE}:resolved"
    rec = seal(
        {
            "record_type": "receipt",
            "receipt_id": f"rcpt_{CASE[5:]}_decline",
            "conversation_id": CASE,
            "did_what": {
                "action": {"tool": "photos.verify"},
                "decision": "declined: outside "
                f"{WINDOW} h window",
            },
        },
        GENESIS,
    )
    first = seal(
        {
            "record_type": "outcome",
            "receipt_id": rec["receipt_id"],
            "recorded_at": ts(row["due"]),
            "status": "achieved",
            "billable": [
                {"idempotency_key": key, "status": "billed"}
            ],
        },
        rec["integrity"]["hash"],
    )
    second = seal(
        {
            "record_type": "outcome",
            "receipt_id": rec["receipt_id"],
            "recorded_at": ts(UPHELD),
            "status": "reversed",
            "supersedes": first["integrity"]["hash"],
            "reason": "appeal upheld: window measured "
            "from scheduled, not actual, delivery",
            "billable": [
                {"idempotency_key": key, "status": "credited"}
            ],
        },
        first["integrity"]["hash"],
    )
    return [rec, first, second]


def verified(records):
    prev = GENESIS
    for r in records:
        if r["integrity"]["prev_hash"] != prev:
            return False
        if record_hash(r) != r["integrity"]["hash"]:
            return False
        prev = r["integrity"]["hash"]
    return True


def refund(case):
    """The corrected refund, on an approval bound to it."""
    amount = f"{case['cents'] / 100:.2f}"
    call = gw.refund(case["order_id"], amount)
    at = int(UPHELD.timestamp())
    basis = {
        "kind": "approval",
        "id": "apr_31",
        "order": case["order_id"],
        "amount": amount,
        "expires": at + 15 * 60,
    }
    pay = Payments()
    status, pid = pay.pay(
        token(call, basis, f"op_{CASE}", at), at
    )
    return amount, status, pid, pay


def run():
    declined, quiet, billed_feb, case, row = february()
    records = chain(case, row)
    amount, status, pid, pay = refund(case)
    return {
        "declined": declined,
        "quiet": quiet,
        "billed_feb": billed_feb,
        "case": case,
        "row": row,
        "records": records,
        "verified": verified(records),
        "amount": amount,
        "paid": (status, pid),
        "ledger": pay.ledger,
    }


def show(r):
    c, row = r["case"], r["row"]
    seen = c["at"].strftime("%b %d %H:%M")
    due = row["due"].strftime("%b %d %H:%M")
    hours, real = c["hours"], c["hours"] - LATE_H
    n_q = len(r["quiet"])
    lines = [
        "Appealed refund: Hilltop, Feb 2027",
        "declines in February           "
        f"{len(r['declined']):>3}",
        f"  came back within 7 days      "
        f"{len(r['declined']) - n_q:>3}",
        f"  went quiet: counted resolved {n_q:>3}",
        f"The case: {CASE}, {c['order_id']}, "
        f"{c['item']} ${r['amount']}",
        f"  {seen}  photo {hours} h after scheduled delivery",
        f"                declined: window is {WINDOW} h",
        f"                van {LATE_H} h late: {real} h after "
        "delivery",
        f"  {due}  outcome: achieved, no return in 7 days",
        f"  Feb 28        billed on February invoice  ${PRICE}",
        f"  Mar 08 10:02  customer appeals by email",
        f"  Mar 08 10:40  appeal upheld; apr_31, Hilltop lead",
        f"                refund {r['paid'][1]} "
        f"${r['amount']}, basis approval",
        "                outcome: reversed, supersedes"
        " achieved",
        "  Mar 09        eval case: window from delivered_at",
        "  Mar 10        photos.verify reads delivered_at",
        f"  Mar 31        credit on March invoice    -${PRICE}",
        f"chain: {len(r['records'])} records, "
        + ("verified" if r["verified"] else "BROKEN")
        + "; nothing edited",
        f"silent declines billed in February: "
        f"{len(r['billed_feb'])} of {n_q}",
    ]
    return lines


def main():
    print("\n".join(show(run())))


if __name__ == "__main__":
    main()
