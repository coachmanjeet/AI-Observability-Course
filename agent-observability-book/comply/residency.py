"""Residency and localization for agents (Chapter 32).

Usage: python -m comply.residency [OUT_DIR]

Every hop in a conversation (model call, tool call, context
fetch, trace export, receipt write) declares where it runs and
what class of data it carries. A tenant's residency policy says
which regions may process each class. The router checks the
policy before each hop, fails over only within allowed regions,
and records the result in the receipt's where section.
"""
import json
import pathlib
import sys

REGIONS = {"us-west-2": "US", "us-east-1": "US",
           "eu-west-1": "EU", "eu-central-1": "EU"}
# which data classes must stay in the tenant's residency
RESTRICTED = {"personal", "metadata"}
TENANTS = {"tenant:pronto": "US", "tenant:fresca": "EU"}
MODELS = {"US": ["us-west-2", "us-east-1"],
          "EU": ["eu-west-1", "eu-central-1"]}


# one agent version, localized by profile, not by fork
AGENT = "agent://pronto/speedy@2.3.1"
LOCALES = {
    "tenant:pronto": {"locale": "en-US", "currency": "USD",
                      "refund_limit": "50.00",
                      "pack": "pronto-support@1.4.0",
                      "memory": "us-west-2"},
    "tenant:fresca": {"locale": "en-IE", "currency": "EUR",
                      "refund_limit": "45.00",
                      "pack": "pronto-support-ie@1.0.0",
                      "memory": "eu-west-1"},
}


def localize(tenant):
    """The profile an agent runs with for this tenant."""
    return {"agent": AGENT, **LOCALES[tenant]}


def allowed(tenant, region, data):
    """May this tenant's data of this class go to region?"""
    if data not in RESTRICTED:
        return True
    return REGIONS[region] == TENANTS[tenant]


def pick_model(tenant, down=()):
    """First healthy model endpoint the policy allows."""
    for region in MODELS["US"] + MODELS["EU"]:
        if region in down:
            continue
        if allowed(tenant, region, "personal"):
            return region
    return None


HOPS = [("model call", "model", "personal"),
        ("orders.get (MCP)", "eu-west-1", "personal"),
        ("context pack", "us-west-2", "public"),
        ("trace export", "eu-west-1", "metadata"),
        ("receipt store", "eu-west-1", "personal"),
        ("analytics copy", "us-west-2", "personal")]


def conversation(tenant, down=()):
    rows, model = [], pick_model(tenant, down)
    for name, region, data in HOPS:
        region = model if region == "model" else region
        ok = allowed(tenant, region, data)
        rows.append((name, region, data,
                     "ok" if ok else "blocked"))
    return model, rows


def where(tenant, model, region):
    return {"cloud_provider": "aws", "region": region,
            "environment": "production",
            "data_residency": TENANTS[tenant],
            "model_endpoint_region": model}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    down = ("eu-west-1",)
    model, rows = conversation("tenant:fresca", down)
    print("Fresca (EU residency), Sep 6, 2027; eu-west-1 model "
          "down")
    print(f"{'hop':<19}{'region':<14}{'data':<10}result")
    for name, region, data, result in rows:
        print(f"{name:<19}{region:<14}{data:<10}{result}")
    blind = next(r for r in MODELS["US"] + MODELS["EU"]
                 if r not in down)
    print(f"a residency-blind failover would pick {blind}")
    us_model, _ = conversation("tenant:pronto")
    w = where("tenant:fresca", model, "eu-west-1")
    print("localized, same agent " + AGENT.split("@")[1] + ":")
    for t in ("tenant:pronto", "tenant:fresca"):
        L = localize(t)
        print(f"  {t[7:]:<7}{L['locale']:<7}{L['currency']} "
              f"{L['refund_limit']:<7}{L['pack']:<24}"
              f"{L['memory']}")
    print("receipt where:")
    for k, v in w.items():
        print(f"  {k:<22}{v}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "where-pronto.json").write_text(json.dumps(
            {"where": where("tenant:pronto", us_model,
                            "us-west-2")}, indent=2) + "\n")
        (out / "where-fresca.json").write_text(json.dumps(
            {"where": w}, indent=2) + "\n")


if __name__ == "__main__":
    main()
