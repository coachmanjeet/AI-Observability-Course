"""Chapter 20: red-teaming the fleet."""
from policy.redteam import (REFUNDS_TOOL, Breaker, attacks,
                            egress_ok, normal, pinned)


def test_nine_of_ten_blocked_and_the_gap_is_asi09():
    rows, _ = attacks()
    gaps = [r[0] for r in rows if not r[2]]
    assert len(rows) == 10 and gaps == ["ASI09"]


def test_no_false_blocks():
    assert all(normal())


def test_tool_pin_catches_any_change():
    assert pinned(REFUNDS_TOOL)
    changed = {**REFUNDS_TOOL, "inputSchema": {"type": "object"}}
    assert not pinned(changed)


def test_egress_is_allowlisted():
    assert egress_ok("coder", "github.com")
    assert not egress_ok("coder", "paste.example.net")
    assert not egress_ok("speedy", "github.com")


def test_breaker_opens_after_three():
    b = Breaker()
    assert [b.allow("k") for _ in range(5)] == \
        [True, True, True, False, False]


def test_every_blocked_gateway_call_has_a_deny_record():
    rows, records = attacks()
    assert {r["threat"] for r in records} == {
        "ASI01", "ASI02", "ASI03", "ASI04", "ASI05", "ASI07",
        "ASI08", "ASI10"}
    assert all(r["under_which_rule"]["decision"] == "deny"
               and r["did_what"]["effect"]["status"] == "blocked"
               for r in records)
    assert sum(r["count"] for r in records) == 29


def test_breaker_lets_three_through_and_one_refund_lands():
    from policy.redteam import LOOP, attacks
    attacks()
    attacks()
    assert LOOP == {"issued": 1, "already": 2, "blocked": 22}
