"""Chapter 21: break-glass and in-flight revocation."""
from policy.breakglass import run

ROWS = {label: (outcome, why) for label, outcome, why in run()}


def test_two_people_and_a_ceiling():
    assert ROWS["self-approved grant"][0] == "refused"
    assert ROWS["$120 under the grant"][0] == "allow"
    assert ROWS["$180 under the grant"][0] == "deny"


def test_a_grant_never_beats_a_forbid_or_the_owner():
    assert ROWS["$120, payments freeze"] == ("deny",
                                             "payments-freeze")
    assert ROWS["$120, another customer"][0] == "deny"


def test_the_grant_expires_and_is_reviewed():
    assert ROWS["$120 after expiry"][0] == "deny"
    assert ROWS["review at expiry"][1] == "1 action under bg_01"


def test_revocation_stops_an_authorized_call():
    assert ROWS["authorized, then run"][0] == "allow"
    assert ROWS["revoked before it ran"][0] == "reject"
