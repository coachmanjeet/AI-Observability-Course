"""Chapter 8: reconcile payments against receipts."""
from audit.recover import night, pause_at, rebuild, reconcile

LEDGER, RECEIPTS, DECISIONS, RETRIES = night()
FINDINGS = [f for _, f in reconcile(LEDGER, RECEIPTS)]


def test_three_problems_told_apart():
    gap = "missing receipt"
    assert FINDINGS == ["ok", gap, gap, gap,
                        "duplicate receipt (2 for 1)",
                        "duplicate payment"]


def test_a_retry_is_the_same_payment():
    assert [(op, pid) for _, op, pid in RETRIES] == \
        [("op_a2", "pay_0002")]
    assert len(LEDGER) == 6


def test_writes_pause_after_three_gaps():
    assert pause_at(reconcile(LEDGER, RECEIPTS)) == 15


def test_a_rebuilt_receipt_says_what_it_does_not_know():
    states = {s: v for s, _, v in rebuild(LEDGER[1], {})}
    assert states["knowing what"] == "unknown"
    assert states["did what"] == "witnessed"
