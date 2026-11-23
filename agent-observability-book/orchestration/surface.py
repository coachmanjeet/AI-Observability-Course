"""Pronto's agent-facing MCP surface (Chapter 20).

Usage: python -m orchestration.surface [OUT_DIR]

Customers' and partners' agents call Pronto's catalog and orders
through one MCP surface. Clients identify themselves with a
Client ID Metadata Document (a URL) and may sign requests; each
tool states the tier it needs; consequential calls need a token
the customer granted to that client; large orders ask the
customer to confirm; and Pronto writes a receipt naming the
external agent and the customer it acted for.
"""
import hashlib
import json
import pathlib
import sys

# known client metadata documents (fetched and cached in prod)
CLIENTS = {
    "https://shopper.example/oauth/client.json": {
        "agent_id": "agent://shopper.example/assistant",
        "name": "Shopper Assistant", "tier": "delegated"},
    "https://reseller.example/oauth/client.json": {
        "agent_id": "agent://reseller.example/buyer",
        "name": "Reseller Buyer", "tier": "partner"},
}
TOOLS = {"catalog.search": "public",
         "cart.add": "delegated",
         "orders.place": "delegated"}
SCOPES = {"cart.add": "cart:write:own",
          "orders.place": "orders:place:own"}
CONFIRM_OVER = 150
PUBLIC_PER_MIN = 120
RANK = {"public": 0, "delegated": 1, "partner": 1}


def session_id(client, customer):
    h = hashlib.sha256(f"{client}|{customer}".encode())
    return "mcps_" + h.hexdigest()[:8]


class Surface:
    def __init__(self):
        self.calls, self.receipts = {}, []

    def tier(self, client, signed):
        known = CLIENTS.get(client)
        if known and signed:
            return known["tier"]
        return "public"

    def call(self, client, tool, signed=True, grant=None,
             amount=None, confirmed=False):
        """One tools/call; returns what the agent sees."""
        tier = self.tier(client, signed)
        if tier == "public":
            n = self.calls.get(client, 0) + 1
            self.calls[client] = n
            if n > PUBLIC_PER_MIN:
                return "429: slow down"
        if RANK[tier] < RANK[TOOLS[tool]]:
            return "401: sign in and grant access"
        need = SCOPES.get(tool)
        if need and (not grant or need not in grant["scopes"]):
            return f"403: needs {need}"
        if tool == "orders.place":
            if amount > CONFIRM_OVER and not confirmed:
                return "ask customer to confirm"
            self.receipts.append(self.receipt(client, grant,
                                              amount))
            return "placed, receipt written"
        return "ok"

    def receipt(self, client, grant, amount):
        c, cust = CLIENTS[client], grant["customer"]
        return {
            "who": {"agent_id": c["agent_id"],
                    "agent_name": c["name"],
                    "kind": "third_party",
                    "owner": "external:"
                             + client.split("/")[2]},
            "for_whom": {
                "principal_type": "user", "principal_id": cust,
                "delegation_chain": [{
                    "actor": c["agent_id"],
                    "via": "oauth_authorization_code",
                    "scopes": grant["scopes"]}]},
            "did_what": {"action": {"tool": "orders.place",
                                    "via": "mcp"},
                         "effect": {"amount": {
                             "value": f"{amount:.2f}",
                             "currency": "USD"}}},
            "evidence": {"mcp_session_id":
                         session_id(client, cust)}}


SHOPPER = "https://shopper.example/oauth/client.json"
UNKNOWN = "https://scraper.example/client.json"
GRANT = {"customer": "cust_7f3a91",
         "scopes": ["cart:write:own", "orders:place:own"]}


def demo():
    s, rows = Surface(), []
    rows.append(("Shopper Assistant, signed", None))
    for label, kw in [
            ("  catalog.search", dict(tool="catalog.search")),
            ("  cart.add", dict(tool="cart.add", grant=GRANT)),
            ("  orders.place $64.20",
             dict(tool="orders.place", grant=GRANT,
                  amount=64.20)),
            ("  orders.place $212.00",
             dict(tool="orders.place", grant=GRANT,
                  amount=212.00)),
            ("  ... customer confirms",
             dict(tool="orders.place", grant=GRANT,
                  amount=212.00, confirmed=True)),
            ("  orders.place, no grant",
             dict(tool="orders.place", amount=20.0))]:
        rows.append((label, s.call(SHOPPER, **kw)))
    rows.append(("Same client, unsigned", None))
    rows.append(("  cart.add",
                 s.call(SHOPPER, "cart.add", signed=False,
                        grant=GRANT)))
    rows.append(("Unknown client", None))
    results = [s.call(UNKNOWN, "catalog.search", signed=False)
               for _ in range(130)]
    ok = results.count("ok")
    rows.append(("  catalog.search x130/min",
                 f"{ok} ok, then {results[-1]}"))
    return s, rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    s, rows = demo()
    print("pronto-shop MCP surface, Apr 12, 2027")
    for label, result in rows:
        print(label if result is None
              else f"{label:<27}{result}")
    print(f"receipts written: {len(s.receipts)}, each naming "
          "the agent")
    print("  and the customer it acted for")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        r = s.receipts[0]
        keep = {k: r[k] for k in ("who", "evidence")}
        (out / "external-receipt.json").write_text(
            json.dumps(keep, indent=2) + "\n")


if __name__ == "__main__":
    main()
