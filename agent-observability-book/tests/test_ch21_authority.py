"""Chapter 21: authority checked at the decision and at payment."""
from policy.authority import run

ROWS, PAY = run()
RESULT = {label: result for label, _, _, result in ROWS}


def test_each_path_pays_once_with_its_basis():
    assert [e["basis"] for e in PAY.ledger] == [
        "delegated", "approval", "break-glass"]


def test_payment_rechecks_authority_above_50():
    assert RESULT["$85, token without approval"] == (
        "reject", "above $50 needs an approval or grant")
    assert RESULT["$85, approval presented at 14:25"] == (
        "reject", "approval apr_01 expired")


def test_retry_with_the_same_key_is_the_same_payment():
    from pronto.payments import token
    from policy import gateway as gw
    from policy.authority import T0
    call = gw.refund("ord_5521", "40.00")
    basis = {"kind": "delegated"}
    raw = token(call, basis, "op_1", T0 + 5)
    assert PAY.pay(raw, T0 + 5) == ("same", "pay_0001")
