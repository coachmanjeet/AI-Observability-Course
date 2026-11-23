"""Observe and enforce, side by side (Chapter 34).

Usage: python -m shiphold.modes

Most controls block in either mode, because they act on facts
the control plane holds itself: an identity, a token's scopes,
an amount, an approval, a pause. One rule changes with the mode,
require-r4: a consequential action whose receipt can't answer
all seven questions is denied in enforce mode, and allowed with
a flag in observe mode. Turning it on is what the review
decides.
"""

from policy import gateway as gw

V4 = (gw.HERE / "pronto-refunds-v4.cedar", "4")

# Controls that block in observe mode too: name, chapter, where
ALWAYS = [
    (
        "registered identity, own token",
        "15-16",
        "token service",
    ),
    ("no path around the gateway", "19", "refund, payments"),
    ("refund policy, approvals", "19, 21", "gateway"),
    ("over $50 needs approval or grant", "21", "payments"),
    ("token scopes sized per task", "17-18", "token exchange"),
    ("loop breaker, egress, pinning", "20", "gateway"),
    ("pause and kill switch", "21", "gateway"),
    ("residency routing", "32", "model router"),
]

# Scopes each agent's token carries today (Promo cut in July)
TOKENS = {
    "pick": {"orders:read:aggregate", "picklists:write"},
    "ledger": {"disputes:create"},
    "promo": {"customers:read:optin", "campaigns:draft"},
}

# label, agent, scope needed, receipt level it can reach
OTHERS = [
    ("Pick    nightly batch", "pick", "picklists:write", "R1"),
    (
        "Ledger  open a dispute",
        "ledger",
        "disputes:create",
        "R3",
    ),
    ("Promo   campaign email", "promo", "email:send", "R1"),
]


def always_speedy(amount):
    """Speedy's refund through the real policy, v4."""
    req = gw.request_from(
        gw.refund("ord_5521", amount), {"sub": "cust_7f3a91"}
    )
    req["subject"] = "agent://pronto/speedy"
    d = gw.decide(
        req,
        ["orders:read:own", "refunds:create:max_50"],
        policies=V4,
    )
    return (
        "allow" if d["decision"] == "allow" else "deny: policy"
    )


def always_scope(agent, scope):
    return "allow" if scope in TOKENS[agent] else "deny: scope"


def mode(always, level, which):
    """What happens to one action in one mode."""
    if always != "allow":
        return always
    if level == "R4":
        return "allow"
    return (
        "allow, flagged" if which == "observe" else "deny: R4"
    )


def actions():
    rows = [
        ("Speedy  $40 refund", always_speedy("40.00"), "R4"),
        (
            "Speedy  $85, no approval",
            always_speedy("85.00"),
            "R4",
        ),
    ]
    rows += [
        (label, always_scope(a, s), lvl)
        for label, a, s, lvl in OTHERS
    ]
    return [
        (
            label,
            lvl,
            mode(al, lvl, "observe"),
            mode(al, lvl, "enforce"),
        )
        for label, al, lvl in rows
    ]


def show():
    lines = [
        "Blocks in either mode",
        "  control                          ch     enforced by",
    ]
    for name, ch, where in ALWAYS:
        lines.append(f"  {name:<33}{ch:<7}{where}")
    lines.append("Changes with the mode: require-r4")
    lines.append(
        "  action                   receipt "
        "observe         enforce"
    )
    for label, lvl, obs, enf in actions():
        lines.append(f"  {label:<25}{lvl:<8}{obs:<16}{enf}")
    return lines


def main():
    print("\n".join(show()))


if __name__ == "__main__":
    main()
