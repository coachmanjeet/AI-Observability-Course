"""Chapter 20: governing external agents on Pronto's surface."""
import json
import re

from orchestration.surface import (GRANT, SHOPPER, UNKNOWN,
                                   Surface, session_id)


def test_public_tools_need_no_grant():
    assert Surface().call(UNKNOWN, "catalog.search",
                          signed=False) == "ok"


def test_unknown_or_unsigned_clients_cannot_write():
    s = Surface()
    assert s.call(UNKNOWN, "cart.add", signed=False,
                  grant=GRANT).startswith("401")
    assert s.call(SHOPPER, "cart.add", signed=False,
                  grant=GRANT).startswith("401")


def test_writes_need_the_customers_grant():
    s = Surface()
    assert s.call(SHOPPER, "orders.place",
                  amount=20.0).startswith("403")
    assert s.call(SHOPPER, "orders.place", grant=GRANT,
                  amount=20.0).startswith("placed")


def test_large_orders_ask_the_customer():
    s = Surface()
    assert s.call(SHOPPER, "orders.place", grant=GRANT,
                  amount=212.0) == "ask customer to confirm"
    assert s.call(SHOPPER, "orders.place", grant=GRANT,
                  amount=212.0, confirmed=True).startswith("placed")


def test_public_tier_is_rate_limited():
    s = Surface()
    out = [s.call(UNKNOWN, "catalog.search", signed=False)
           for _ in range(121)]
    assert out[119] == "ok" and out[120].startswith("429")


def test_receipt_names_agent_customer_and_session():
    s = Surface()
    s.call(SHOPPER, "orders.place", grant=GRANT, amount=64.2)
    r = s.receipts[0]
    assert r["who"]["kind"] == "third_party"
    assert r["for_whom"]["principal_id"] == "cust_7f3a91"
    sid = r["evidence"]["mcp_session_id"]
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))
    pat = r"^mcps_[0-9a-f]{8}$"
    assert re.match(pat, sid)
    assert re.match(pat, ex["evidence"]["mcp_session_id"])
    assert sid == session_id(SHOPPER, "cust_7f3a91")
