"""Chapter 26: what blocks in observe mode, and what waits."""
from shiphold import modes

ROWS = {label.split()[0] + " " + label.split()[1]: rest
        for label, *rest in modes.actions()}


def test_policy_and_scope_denies_hold_in_both_modes():
    assert ROWS["Speedy $85,"][1:] == ["deny: policy"] * 2
    assert ROWS["Promo campaign"][1:] == ["deny: scope"] * 2


def test_only_incomplete_receipts_change_with_mode():
    for key in ("Pick nightly", "Ledger open"):
        lvl, obs, enf = ROWS[key]
        assert lvl != "R4"
        assert (obs, enf) == ("allow, flagged", "deny: R4")
    assert ROWS["Speedy $40"][1:] == ["allow", "allow"]
