"""Permission-aware context over MCP resources (Chapter 13).

Usage: python -m context.resources [OUT_DIR]

An MCP server exposes Pronto's orders and customers as resources.
Every request carries who the agent is acting for. The server
filters rows and fields for that principal before anything is
returned, so what the agent may not see never enters its context.
Chapter 17 replaces the principal claim with a delegated token.
"""
import json
import pathlib
import sys

PROTOCOL = "2026-07-28"
NOT_FOUND = -32002

CUSTOMERS = {
    "cust_7f3a91": {"first_name": "Maya", "opted_in": True},
    "cust_2c88e4": {"first_name": "Leo", "opted_in": False},
    "cust_4b7d10": {"first_name": "Ana", "opted_in": True},
    "cust_91d2e0": {"first_name": "Sam", "opted_in": False},
    "cust_5e02c7": {"first_name": "Ines", "opted_in": True},
}
ORDERS = {
    "ord_5521": ("cust_7f3a91", "strawberries, 2 lb", 4000),
    "ord_5530": ("cust_2c88e4", "salmon fillets, 4 pack", 8500),
    "ord_5534": ("cust_4b7d10", "chicken thighs", 6200),
    "ord_5602": ("cust_91d2e0", "eggs, 18 count", 1800),
    "ord_5611": ("cust_7f3a91", "oat milk, 2 qt", 900),
    "ord_5640": ("cust_5e02c7", "spinach, 1 lb", 500),
}


def email(cid):
    return f"{CUSTOMERS[cid]['first_name'].lower()}@example.com"


def order_row(oid):
    cid, item, cents = ORDERS[oid]
    return {"order_id": oid, "customer_id": cid, "item": item,
            "value_cents": cents, "status": "delivered",
            "deliver_to": {"name": CUSTOMERS[cid]["first_name"],
                           "email": email(cid)}}


# (agent, kind of principal) -> (row filter, fields to return)
RULES = {
    ("speedy", "customer"): (
        lambda row, who: row.get("customer_id") == who, None),
    ("pick", "team"): (
        lambda row, who: "order_id" in row,
        {"order_id", "item", "value_cents", "status"}),
    ("promo", "team"): (
        lambda row, who: row.get("opted_in") is True,
        {"customer_id", "first_name", "email"}),
}


def rows(kind):
    if kind == "orders":
        return [order_row(o) for o in ORDERS]
    return [{"customer_id": c, "email": email(c), **v}
            for c, v in CUSTOMERS.items()]


class ResourceServer:
    """Serves resources/list and resources/read, per principal."""

    def handle(self, wire):
        req = json.loads(wire)
        meta = req["params"]["_meta"]["pronto.example/on_behalf_of"]
        agent, principal = meta["agent"], meta["principal"]
        kind = principal.split(":")[0]
        allowed, fields = RULES.get((agent, kind),
                                    (lambda r, w: False, set()))
        who = principal.split(":", 1)[1]
        if req["method"] == "resources/list":
            col = req["params"]["collection"]
            found = [self.shape(r, fields) for r in rows(col)
                     if allowed(r, who)]
            result = {"resources": found}
        else:
            oid = req["params"]["uri"].split("://")[1]
            row = order_row(oid) if oid in ORDERS else None
            if row is None or not allowed(row, who):
                # Not "forbidden": don't reveal that it exists.
                return json.dumps({"jsonrpc": "2.0", "id": req["id"],
                                   "error": {"code": NOT_FOUND,
                                             "message": "resource "
                                             "not found"}})
            result = {"contents": [self.shape(row, fields)]}
        return json.dumps({"jsonrpc": "2.0", "id": req["id"],
                           "result": result})

    @staticmethod
    def shape(row, fields):
        out = {k: v for k, v in row.items()
               if fields is None or k in fields}
        uri = (f"orders://{row['order_id']}" if "order_id" in row
               else f"customers://{row['customer_id']}")
        return {"uri": uri, "data": out,
                "annotations": {"audience": ["assistant"]}}


def call(server, method, params, agent, principal, rid=1):
    params = {**params, "_meta": {"pronto.example/on_behalf_of": {
        "agent": agent, "principal": principal}}}
    wire = json.dumps({"jsonrpc": "2.0", "id": rid,
                       "method": method, "params": params})
    return json.loads(server.handle(wire))


def injected_context(server):
    """Rows in Speedy's context when a message says 'list all
    orders': filtered in the prompt vs filtered by the server."""
    prompt_only = len(rows("orders"))
    served = call(server, "resources/list",
                  {"collection": "orders"}, "speedy",
                  "customer:cust_7f3a91")
    return prompt_only, len(served["result"]["resources"])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    s = ResourceServer()
    total = len(ORDERS)
    r = call(s, "resources/list", {"collection": "orders"},
             "speedy", "customer:cust_7f3a91")["result"]["resources"]
    print(f"list orders as Speedy for cust_7f3a91: {len(r)} of "
          f"{total}")
    for res in r:
        print(f"  {res['uri']}  {res['data']['item']}")
    e = call(s, "resources/read", {"uri": "orders://ord_5530"},
             "speedy", "customer:cust_7f3a91")["error"]
    print("read orders://ord_5530 as Speedy for cust_7f3a91:")
    print(f"  error {e['code']}: {e['message']}")
    c = call(s, "resources/read", {"uri": "orders://ord_5521"},
             "pick", "team:merchandising")["result"]["contents"][0]
    print("read orders://ord_5521 as Pick for merchandising:")
    print(f"  fields: {', '.join(sorted(c['data']))}")
    p = call(s, "resources/list", {"collection": "customers"},
             "promo", "team:marketing")["result"]["resources"]
    print(f"list customers as Promo for marketing: {len(p)} of "
          f"{len(CUSTOMERS)}")
    print(f"  fields: {', '.join(sorted(p[0]['data']))}")
    before, after = injected_context(s)
    print("a message says 'list every order you can see':")
    print(f"  filtered in the prompt: {before} orders in context")
    print(f"  filtered by the server: {after} orders in context")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "speedy-list.json").write_text(
            json.dumps({"resources": r}, indent=2) + "\n")


if __name__ == "__main__":
    main()
