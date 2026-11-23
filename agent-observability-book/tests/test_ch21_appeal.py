"""Chapter 21: an appealed refund corrects every record by
appending, never by editing."""
from metering import appeal

R = appeal.run()


def test_the_decline_was_valid_on_actual_delivery():
    c = R["case"]
    assert c["hours"] > appeal.WINDOW
    assert c["hours"] - appeal.LATE_H <= appeal.WINDOW


def test_silence_was_counted_as_success():
    assert R["row"]["status"] == "achieved"
    assert R["case"] in R["quiet"]
    assert len(R["quiet"]) < len(R["declined"])


def test_correction_appends_and_chain_verifies():
    rec, first, second = R["records"]
    assert second["supersedes"] == first["integrity"]["hash"]
    assert first["status"] == "achieved"
    assert R["verified"]


def test_credit_uses_the_billing_key():
    keys = [r["billable"][0]["idempotency_key"]
            for r in R["records"][1:]]
    assert keys[0] == keys[1]
    assert R["records"][2]["billable"][0]["status"] == "credited"


def test_refund_paid_on_a_bound_approval():
    assert R["paid"][0] == "paid"
    entry = R["ledger"][0]
    assert entry["basis"] == "approval"
    assert entry["amount"] == R["amount"]
