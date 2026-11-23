"""Metering agent work from receipts and outcomes (Chapter 28).

Usage: python -m metering.usage [OUT_DIR]

Pronto sells Speedy to other grocers and bills them per resolved
conversation. This lab derives usage events from a month of
spans for two tenants: a pending event when the conversation
happens, a billed event when its outcome record arrives, and a
credit when a sampled review reverses one. Exporter retries
duplicate some spans; idempotency keys make the duplicates
harmless. Outcomes that arrive after the period closes are
billed on the next invoice with their original service date.
"""
import hashlib
import json
import pathlib
import sys
from collections import Counter
from datetime import timedelta
from decimal import Decimal

from metering.traffic import day, month
from metering.value import by_conversation, outcomes

RATE = Decimal("0.40")          # per resolved conversation
CLOSE = day("2027-03-01")       # February closes, midnight UTC
TENANTS = ["tenant:hilltop", "tenant:bayside"]


def h(text):
    digest = hashlib.sha256(text.encode()).hexdigest()
    return int(digest[:8], 16)


def events(tenant, spans, convs):
    """Usage events for one tenant, with retries duplicated."""
    per = by_conversation(spans)
    rows = {r["conversation_id"]: r
            for r in outcomes(convs, per)}
    out = []
    for c in convs:
        cid = c["conversation_id"]
        if cid not in rows:
            continue
        key = f"{cid}:resolved"
        base = {"tenant": tenant,
                "agent": "agent://pronto/speedy",
                "customer": c["customer_id"],
                "meter": "resolved_conversation",
                "idempotency_key": key,
                "service_date": c["at"].date().isoformat()}
        out.append({**base, "status": "pending_outcome",
                    "quantity": 0, "at": c["at"]})
        if h(cid) % 50 == 0:        # an exporter retry
            out.append({**base, "status": "pending_outcome",
                        "quantity": 0, "at": c["at"]})
        r = rows[cid]
        if r["status"] == "achieved":
            out.append({**base, "status": "billed",
                        "quantity": 1, "at": r["due"]})
            if h(cid + "review") % 100 == 0:
                out.append({**base, "status": "credited",
                            "quantity": -1,
                            "idempotency_key": key + ":credit",
                            "at": r["due"] + timedelta(days=2)})
    return out


def dedupe(evts):
    seen, kept = set(), []
    for e in evts:
        k = (e["idempotency_key"], e["status"])
        if k not in seen:
            seen.add(k)
            kept.append(e)
    return kept, len(evts) - len(kept)


def invoice(evts):
    """February's invoice and what moves to March."""
    feb = [e for e in evts if e["at"] < CLOSE
           and e["status"] in ("billed", "credited")]
    late = [e for e in evts if e["at"] >= CLOSE
            and e["status"] == "billed"
            and e["service_date"] < "2027-03-01"]
    qty = sum(e["quantity"] for e in feb)
    return {"lines": Counter(e["status"] for e in feb),
            "quantity": qty, "amount": qty * RATE,
            "late": len(late)}


def run():
    out = {}
    for tenant in TENANTS:
        spans, convs = month(tenant, day("2027-02-01"), 28)
        raw = events(tenant, spans, convs)
        kept, dupes = dedupe(raw)
        out[tenant] = {"raw": raw, "kept": kept, "dupes": dupes,
                       "convs": sum(not c["follow_up"]
                                    for c in convs),
                       "invoice": invoice(kept)}
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    res = run()
    print("Usage events, Feb 2027: "
          "resolved_conversation at $0.40")
    print(f"{'tenant':<16}{'firsts':>7}{'dupes':>7}"
          f"{'gross':>8}{'credit':>8}{'late':>6}"
          f"{'amount':>10}")
    for t, r in res.items():
        inv = r["invoice"]
        print(f"{t:<16}{r['convs']:>7,}{r['dupes']:>7}"
              f"{inv['lines']['billed']:>8,}"
              f"{inv['lines']['credited']:>8}{inv['late']:>6}"
              f"{'$' + format(inv['amount'], ',.2f'):>10}")
    print("late = resolved after Feb 28 close; "
          "on March invoice")
    print("amount = (gross - credit) x price per resolution")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        first = res[TENANTS[0]]["kept"][0]
        billable = {k: first[k] for k in
                    ("meter", "quantity", "status",
                     "idempotency_key")}
        (out / "billable.json").write_text(json.dumps(
            {"at_what_cost": {"billable": [billable]}},
            indent=2) + "\n")


if __name__ == "__main__":
    main()
