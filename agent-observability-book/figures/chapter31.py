"""Chapter 31 figures: one piece of evidence, many requirements.

Usage: python -m figures.chapter31 OUT_DIR
"""

import pathlib
import sys

from figures.chapter02 import receipt_strip
from figures.notation import FILL, MID, PALE, box, svg, text
from comply.evidence import pack

FWS = ["EU AI Act", "ISO 42001", "NIST AI RMF"]
NAMES = {
    "receipts": "receipts + chain",
    "denies": "deny records",
    "oversight": "tiers, approvals",
    "retention": "retention",
    "disclosure": "AI disclosure",
    "impact": "impact assessment",
    "monitoring": "canary, tower",
    "provenance": "sources",
    "third_party": "partner receipts",
    "inventory": "registry",
    "deactivate": "pause, revoke",
}


def matrix():
    """Figure 31.2. Rows: evidence. Columns: frameworks."""
    rows = pack()
    checks = list(dict.fromkeys(r["check"] for r in rows))
    x0, y0, cw, rh = 150, 34, 96, 22
    body = [
        text(
            x0 + i * cw + cw / 2,
            22,
            fw,
            size=11.5,
            weight=700,
            anchor="middle",
        )
        for i, fw in enumerate(FWS)
    ]
    for j, chk in enumerate(checks):
        y = y0 + j * rh
        body.append(text(4, y + 15, NAMES[chk], size=11.5))
        for i, fw in enumerate(FWS):
            hits = [
                r
                for r in rows
                if r["check"] == chk and r["fw"] == fw
            ]
            if not hits:
                continue
            st = hits[0]["status"]
            fill = {"met": FILL, "partial": PALE}.get(
                st, "#fff"
            )
            kind = "3P" if st == "gap" else None
            body.append(
                box(
                    x0 + i * cw + 8,
                    y + 3,
                    cw - 16,
                    rh - 6,
                    fill=fill,
                    r=3,
                    kind=kind,
                )
            )
            label = ", ".join(h["id"] for h in hits)
            body.append(
                text(
                    x0 + i * cw + cw / 2,
                    y + 15,
                    label,
                    size=11.5,
                    anchor="middle",
                )
            )
    y = y0 + len(checks) * rh + 10
    body += [
        box(4, y, 16, 12, fill=FILL, r=2),
        text(26, y + 11, "met", size=11.5, fill=MID),
        box(80, y, 16, 12, fill=PALE, r=2),
        text(102, y + 11, "partial", size=11.5, fill=MID),
        box(170, y, 16, 12, r=2, kind="3P"),
        text(192, y + 11, "gap", size=11.5, fill=MID),
    ]
    return svg(y + 20, body)


FIGURES = {
    "fig-31-1-receipt-strip": lambda: receipt_strip(
        {0, 1, 2, 3, 4, 5, 6}
    ),
    "fig-31-2-crosswalk": matrix,
}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(
            draw(), encoding="utf-8"
        )
        print("wrote", out / f"{name}.svg")
