"""Chapter 17: delegation and consent by token exchange."""
import json

import jwt

from identity import workload as wl
from identity.delegation import (AS, ASK, CONSENTS, NOW, SPEEDY,
                                 TTL, check, exchange, for_whom,
                                 login)

R = "refunds:create:max_50"


def delegated():
    svid, _ = wl.attest(wl.SPEEDY, AS)
    token, why = exchange(login("cust_7f3a91"), svid, ASK)
    assert why == "issued"
    return token


def test_token_names_customer_and_agent():
    c = jwt.decode(delegated(), options={"verify_signature": False})
    assert c["sub"] == "cust_7f3a91"
    assert c["act"] == {"sub": SPEEDY}
    assert c["exp"] - c["iat"] == TTL


def test_gateway_enforces_scope_owner_and_limit():
    t = delegated()
    assert check(t, R, amount=40) == "ok"
    assert check(t, R, amount=85) == "over the delegated limit"
    assert check(t, "orders:read:own", owner="cust_2b8c04") == \
        "not the principal's own"
    assert check(t, "orders:read:any") == "scope not delegated"
    assert check(t, R, amount=40, now=NOW + TTL) == "expired"


def test_no_passthrough():
    assert check(login("cust_7f3a91"), R, amount=40) == \
        "wrong audience"


def test_capabilities_and_consent_bound_the_exchange():
    svid, _ = wl.attest(wl.SPEEDY, AS)
    s = login("cust_7f3a91")
    assert exchange(s, svid, ["refunds:create:max_500"])[0] is None
    assert exchange(s, None, ASK)[1] == "no actor token"
    other = login("cust_2b8c04")
    assert exchange(other, svid, ASK)[1].startswith(
        "not consented")
    assert exchange(other, svid, ["orders:read:own"])[1] == \
        "issued"


def test_withdrawn_consent_stops_new_tokens():
    svid, _ = wl.attest(wl.SPEEDY, AS)
    saved = CONSENTS.pop(("cust_7f3a91", SPEEDY))
    try:
        assert exchange(login("cust_7f3a91"), svid, ASK)[1] == \
            "no consent on record"
    finally:
        CONSENTS[("cust_7f3a91", SPEEDY)] = saved


def test_for_whom_matches_chapter_2():
    got = for_whom(delegated())
    ex = json.load(open("receipts/examples/"
                        "02-speedy-refund-40.json"))["for_whom"]
    assert got["token_ref"].startswith("sha256:")
    got.pop("token_ref"), ex.pop("token_ref")
    assert got == ex
