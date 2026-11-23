"""Human oversight that scales (Chapter 16).

Usage: python -m policy.oversight [OUT_DIR]

Autonomy tiers by amount, deterministic sampled review,
approvals that show the facts from Pronto's systems next to the
agent's summary and are bound to one order and amount, and
graduated responses from monitor to revoke.
"""
import hashlib
import json
import pathlib
import sys
from decimal import Decimal

import yaml

from identity import workload as wl
from policy import gateway as gw

HERE = pathlib.Path(__file__).parent
V4 = (HERE / "pronto-refunds-v4.cedar", "4")
NOW = "2027-03-09T14:05:00Z"
EXPIRES = "2027-03-09T14:20:00Z"    # 15 minutes

# facts from the order and payments systems, not from the agent
FACTS = {
    "ord_5602": {"total": "92.40", "photo": True,
                 "refunds_30d": 0},
    "ord_5640": {"total": "62.00", "photo": False,
                 "refunds_30d": 3},
}


def tier_for(amount):
    rows = yaml.safe_load((HERE / "tiers.yaml").read_text())
    for row in rows:
        if row["up_to"] is None or \
                Decimal(amount) <= Decimal(row["up_to"]):
            return row
    raise ValueError(amount)


def sampled(receipt_id, pct):
    """Same receipt, same answer: reviewers can't be gamed."""
    h = hashlib.sha256(receipt_id.encode()).digest()
    return int.from_bytes(h[:4], "big") % 100 < pct


def disagreements(order, claims):
    """Where the agent's summary disagrees with the facts."""
    f, out = FACTS[order], []
    if Decimal(claims["amount"]) > Decimal(f["total"]):
        out.append("amount")
    if claims["photo"] and not f["photo"]:
        out.append("photo")
    if claims["refunds_30d"] != f["refunds_30d"]:
        out.append("history")
    return out


def approve(order, amount, claims, approver, approval_id="apr_01"):
    """An approval bound to one order and amount, or not. v0.1 has
    no fields for the binding, so the method string carries it."""
    bad = disagreements(order, claims)
    if bad:
        return None, f"rejected: {len(bad)} claims disagree"
    record = {"approver": approver, "decided_at": NOW,
              "decision": "approved",
              "method": f"{approval_id} {order} ${amount} "
                        f"until {EXPIRES[11:16]}Z"}
    ctx = {"role": "support_lead",
           "resource": {"__entity": {"type": "Pronto::Order",
                                     "id": order}},
           "amount": {"__extn": {"fn": "decimal",
                                 "arg": amount}}}
    return (record, ctx), "approved"


def request(order, amount, customer="cust_7f3a91"):
    return {"subject": "agent://pronto/speedy",
            "action": "refunds.create",
            "resource": f"order:{order}",
            "context": {"amount": amount, "currency": "USD",
                        "on_behalf_of": customer}}


SCOPES = ["orders:read:own", "refunds:create:max_50"]


def refund_with(order, amount, approval):
    rec, ctx = approval
    d = gw.decide(request(order, amount), SCOPES, at=NOW,
                  policies=V4, approval=ctx)
    if d["decision"] == "allow":
        d["decision"] = "allow_with_approval"
        d["approvals"] = [rec]
    d["autonomy_tier"] = tier_for(amount)["tier"]
    return d


def gate(amount, tier=None, approval=None, rid="rcpt_x"):
    """The gateway's tier check, then Cedar."""
    t = tier or tier_for(amount)
    if t["tier"] == "act_with_approval" and not approval:
        return "held for approval"
    if t["tier"] == "suggest_only":
        return "draft only"
    d = gw.decide(request("ord_5521", amount), SCOPES)
    out = f"{d['decision']}  {d['determining_policies'][0]}"
    if d["decision"] == "allow" and \
            sampled(rid, t.get("sample_pct", 0)):
        out = f"{d['decision']}, sampled for review"
    return out


def respond(level, amount="40.00"):
    """What a $40 refund gets at each response level."""
    speedy = "agent://pronto/speedy"
    if level == "monitor":
        tier = {**tier_for(amount), "sample_pct": 100}
        return gate(amount, tier)
    if level == "restrict":
        return gate(amount, {"tier": "act_with_approval"})
    if level == "pause":
        gw.AGENTS[speedy] = "paused"
        try:
            return gate(amount)
        finally:
            gw.AGENTS[speedy] = "approved"
    wl.APPROVED.discard(speedy)
    try:
        token, _ = wl.attest(wl.SPEEDY, wl.GW)
        return "issued" if token else "no identity issued"
    finally:
        wl.APPROVED.add(speedy)


def demo():
    rows = ["Tiers for refunds.create (policy v4)"]
    for amt in ("8.00", "40.00", "85.00", "900.00"):
        t = tier_for(amt)
        pct = f" ({t['sample_pct']}%)" if "sample_pct" in t \
            else ""
        rows.append(f"  ${amt:<8}{t['tier']}{pct}")
    n = sum(sampled(f"rcpt_speedy_{i:04d}", 5)
            for i in range(588))
    rows.append(f"Sampled review: {n} of Speedy's 588 refunds")
    claims = {"amount": "85.00", "photo": True,
              "refunds_30d": 0}
    ok, why = approve("ord_5602", "85.00", claims, "user:lead-ana")
    d = refund_with("ord_5602", "85.00", ok)
    rows += ["$85 refund, ord_5602",
             "  facts match Speedy's summary",
             f"  support lead approves    {d['decision']}"]
    reuse = [("  same approval, $95", "ord_5602", "95.00"),
             ("  same approval, ord_5521", "ord_5521", "85.00")]
    for label, order, amt in reuse:
        e = refund_with(order, amt, ok)
        rows.append(f"{label:<27}{e['decision']}  "
                    f"{e['determining_policies'][0]}")
    lie = {"amount": "400.00", "photo": True, "refunds_30d": 0}
    _, why = approve("ord_5640", "400.00", lie, "user:lead-ana",
                     "apr_02")
    rows += ["ASI09: $400 refund, ord_5640",
             "  Speedy says: $400, photo, no past refunds",
             "  facts: $62.00 order, no photo, 3 refunds",
             f"  approval service         {why}"]
    rows.append("Graduated responses, $40 refund")
    for level in ("monitor", "restrict", "pause", "revoke"):
        rows.append(f"  {level:<10}{respond(level)}")
    return d, rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    d85, rows = demo()
    print("\n".join(rows))
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        t40 = tier_for("40.00")["tier"]
        (out / "rule-40.json").write_text(json.dumps(
            {"under_which_rule": {"autonomy_tier": t40,
                                  "approvals": []}},
            indent=2) + "\n")
        keep = ("decision", "determining_policies",
                "autonomy_tier", "approvals")
        (out / "rule-85.json").write_text(json.dumps(
            {"under_which_rule": {k: d85[k] for k in keep}},
            indent=2) + "\n")


if __name__ == "__main__":
    main()
