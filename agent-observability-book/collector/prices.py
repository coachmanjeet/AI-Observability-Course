"""Prices behind every cost in the book (Chapter 7).

Model prices are USD per million tokens. pronto-mock-1 is the lab's
stand-in model, priced like a mid-tier hosted model; put your
provider's dated price list here instead. Input tokens include cached
ones, as the GenAI conventions count them, so the cached share is
priced at the cache-read rate and only the rest at the input rate.
"""
from decimal import Decimal

MODELS = {"pronto-mock-1": {"input": "4.00", "cache_read": "0.40",
                            "output": "20.00"}}
# Two ways backends bill for traces (list prices, checked Nov 2026):
TRACES_PER_GB = Decimal("0.50")      # per GB stored, like Grafana Cloud
TRACES_PER_1K = Decimal("5.00")      # per trace, like LangSmith's base


def model_cost(model, input_tokens, output_tokens,
               cache_read=0):
    """Exact cost as a decimal string, never a float."""
    p = {k: Decimal(v) for k, v in MODELS[model].items()}
    cost = ((input_tokens - cache_read) * p["input"]
            + cache_read * p["cache_read"]
            + output_tokens * p["output"]) / 1_000_000
    return format(cost.normalize(), "f")
