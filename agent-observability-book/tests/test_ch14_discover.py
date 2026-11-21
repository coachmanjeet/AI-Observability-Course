"""Chapter 14: discovery from seven evidence sources."""
import json

from registry.discover import HERE, INVENTORY, load, scan


def result():
    inv = json.loads(INVENTORY.read_text())
    return scan(load(HERE / "evidence"), inv)


def by_name():
    return {a["name"]: a for a in result()["agents"]}


def test_nine_agents_among_twelve_actors():
    r = result()
    cats = [a["category"] for a in r["actors"]]
    assert (len(cats), cats.count("agent")) == (12, 9)


def test_two_new_shadow_agents_are_found():
    new = [a for a in result()["agents"] if not a["known"]]
    assert sorted(a["name"] for a in new) == ["Ide Assistant",
                                              "Tally"]
    assert all(a["kind"] == "shadow" for a in new)


def test_night_owl_outlives_its_token():
    flags = by_name()["Night Owl"]["flags"]
    assert any(f.startswith("still running after") for f in flags)


def test_shared_credential_is_flagged():
    assert "shares svc:inventory-sync with Inv Sync Job" in \
        by_name()["Tally"]["flags"]


def test_no_mcp_server_is_in_any_inventory():
    servers = result()["mcp_servers"]
    assert len(servers) == 6
    assert "pg-prod" in {s["name"] for s in servers}


def test_unregistered_callers_of_consequential_apis():
    risky = [r["target"] for r in result()["apis"]
             if r["unregistered"]]
    assert risky == ["POST /inventory/adjust", "POST /refunds"]
