"""Chapter 24 figures: what the control tower owns.

Usage: python -m figures.chapter24 OUT_DIR
"""
import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import FILL, MID, PALE, box, svg, text

COLUMNS = [
    ("Centralize", FILL, "platform team",
     ["registry", "identity issuer", "token exchange",
      "gateways, policy engine", "receipt ledger",
      "pause and revoke"]),
    ("Federate", PALE, "business owners",
     ["task catalogs, tiers", "policy rules", "evals",
      "partner contracts", "approvals"]),
    ("Leave at the edge", "#ffffff", "agent teams",
     ["prompts", "model choice", "frameworks",
      "tool code"]),
]


def layers():
    """Figure 24.2. Centralize the controls, not the agents."""
    body, x = [], 4
    for title, fill, owner, items in COLUMNS:
        body.append(box(x, 8, 146, 34, fill=fill, r=4))
        body.append(text(x + 73, 24, title, size=12, weight=700,
                         anchor="middle"))
        body.append(text(x + 73, 37, owner, size=11.5,
                         anchor="middle", fill=MID))
        for i, item in enumerate(items):
            body.append(box(x, 50 + i * 28, 146, 24, r=3))
            body.append(text(x + 73, 66 + i * 28, item, size=11.5,
                             anchor="middle"))
        x += 152
    return svg(50 + 6 * 28 + 8, body)


FIGURES = {"fig-24-1-receipt-strip": lambda: receipt_strip(
               {0, 1, 2, 3, 4, 5, 6}),
           "fig-24-2-control-tower": layers}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
