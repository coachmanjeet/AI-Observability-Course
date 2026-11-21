"""Chapter 13: an MCP resource server that filters per principal."""
from context.resources import (NOT_FOUND, ResourceServer, call,
                               injected_context)

S = ResourceServer()


def listing(agent, principal, collection="orders"):
    r = call(S, "resources/list", {"collection": collection},
             agent, principal)
    return r["result"]["resources"]


def test_a_customer_turn_sees_only_its_orders():
    uris = [r["uri"] for r in listing("speedy",
                                       "customer:cust_7f3a91")]
    assert uris == ["orders://ord_5521", "orders://ord_5611"]


def test_another_customers_order_is_not_found():
    r = call(S, "resources/read", {"uri": "orders://ord_5530"},
             "speedy", "customer:cust_7f3a91")
    assert r["error"]["code"] == NOT_FOUND
    assert "forbidden" not in r["error"]["message"]


def test_pick_gets_orders_without_personal_fields():
    data = listing("pick", "team:merchandising")[0]["data"]
    assert "deliver_to" not in data and "customer_id" not in data


def test_promo_sees_only_opted_in_contacts():
    got = listing("promo", "team:marketing", "customers")
    assert len(got) == 3
    assert all("opted_in" not in r["data"] for r in got)


def test_unknown_pairs_get_nothing():
    assert listing("coder", "team:engineering") == []


def test_server_filtering_bounds_an_injection():
    assert injected_context(S) == (6, 2)
