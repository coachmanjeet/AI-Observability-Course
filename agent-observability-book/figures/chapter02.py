"""Chapter 2 figures: the receipt strip, anatomy, levels and chain.

Usage: python -m figures.chapter02 OUT_DIR
"""
import pathlib
import sys

from figures.notation import (FILL, MID, PALE, WIDTH, agent, arrow, box,
                              gate, line, receipt, store, svg, text, tool)

QUESTIONS = [("Who\nacted?", "4, 15, 16"), ("For\nwhom?", "17, 18"),
             ("Knowing\nwhat?", "6, 9,\n11–13"),
             ("Under\nwhich\nrule?", "19, 21"),
             ("Doing\nwhat?", "4, 5,\n8, 27"), ("At what\ncost?", "7, 28"),
             ("Where?", "32")]


def receipt_strip(highlight=()):
    """The chapter-opener device. highlight: indexes of fields added."""
    cell, x0 = (WIDTH - 8) / 7, 4
    body = []
    for name, first, last in (("Discover", 0, 1), ("Govern", 2, 3),
                              ("Observe", 4, 6)):
        a, b = x0 + first * cell + 4, x0 + (last + 1) * cell - 4
        body += [line([(a, 26), (a, 20), (b, 20), (b, 26)]),
                 text((a + b) / 2, 14, name, size=12, weight=700,
                      anchor="middle")]
    for i, (label, chapters) in enumerate(QUESTIONS):
        x = x0 + i * cell
        on = i in highlight
        body += [box(x, 32, cell, 56, fill=FILL if on else "#ffffff",
                     width=2.2 if on else 1.4),
                 text(x + cell / 2, 64 - label.count("\n") * 7, label,
                      size=11.5, weight=700 if on else 600,
                      anchor="middle"),
                 text(x + cell / 2, 106, chapters, size=11.5,
                      anchor="middle")]
    body.append(text(WIDTH / 2, 146, "Chapters that fill in each answer",
                     size=11.5, italic=True, anchor="middle", fill=MID))
    return svg(154, body)


ROWS = [  # receipt key, sample value, supplying system, shape, chapters
    ("who", "Speedy 2.3.1, first party", "Registry and runtime",
     "store", "4, 15, 16"),
    ("for_whom", "cust_7f3a91, two scopes", "Identity provider",
     "box", "17, 18"),
    ("knowing_what", "pack 1.4.0, three sources", "Context packs, sources",
     "store", "6, 9, 11–13"),
    ("under_which_rule", "allow, sampled review", "Policy gateway",
     "gate", "19, 21"),
    ("did_what", "refund $40, outcome pending", "Tools, systems of record",
     "tool", "4, 5, 8, 27"),
    ("at_what_cost", "$0.0142, one meter", "Meter", "box", "7, 28"),
    ("where", "aws us-west-2, data in US", "Cloud resource attributes",
     "box", "32"),
    ("evidence", "trace 4bf92f35…", "Trace pipeline (OTel)", "box",
     "4, 5"),
    ("integrity", "prev_hash, hash", "Receipt store", "store", "8"),
]


def receipt_anatomy():
    """Figure 2.2. Every field, and the system that supplies it."""
    top, pitch, rx, rw = 14, 46, 214, 210
    body = [receipt(rx, top - 6, rw, len(ROWS) * pitch + 22, width=2.0)]
    for i, (key, value, system, shape, chapters) in enumerate(ROWS):
        cy = top + 21 + i * pitch
        if i:
            heavy = i in (2, 4)
            body.append(line([(rx, cy - 23), (rx + rw, cy - 23)],
                             width=1.4 if heavy else 0.9,
                             dash=None if heavy else "2 2"))
        body += [text(rx + 10, cy - 3, key, size=12, weight=700, mono=True),
                 text(rx + 10, cy + 12, value, size=11.5, fill=MID)]
        label = f"{system}\nCh {chapters}"
        if shape == "store":
            body.append(store(0, cy - 22, 168, 42, label, size=11.5))
        elif shape == "gate":
            body += [gate(18, cy, 16),
                     text(42, cy - 3, system, size=11.5),
                     text(42, cy + 11, f"Ch {chapters}", size=11.5)]
        elif shape == "tool":
            body.append(tool(0, cy - 16, 168, 34, label, size=11.5))
        else:
            body.append(box(0, cy - 16, 168, 33))
            body.append(text(84, cy - 3, system, size=11.5,
                             anchor="middle"))
            body.append(text(84, cy + 11, f"Ch {chapters}", size=11.5,
                             anchor="middle"))
        body.append(arrow([(171, cy), (rx - 4, cy)]))
    for name, first, last in (("Discover", 0, 1), ("Govern", 2, 3),
                              ("Observe", 4, 8)):
        a = top + first * pitch + 2
        b = top + (last + 1) * pitch - 2
        bx = rx + rw + 10
        body += [line([(bx - 4, a), (bx, a), (bx, b), (bx - 4, b)]),
                 f'<text transform="translate({bx + 17},{(a + b) / 2}) '
                 'rotate(-90)" font-family="Inter, sans-serif" '
                 'font-size="12" font-weight="700" text-anchor="middle">'
                 f'{name}</text>']
    return svg(top + len(ROWS) * pitch + 24, body)


LEVELS = [("R1", "Traced", "who acted,\ndoing what", "2 of 7"),
          ("R2", "Identified", "+ for whom", "3 of 7"),
          ("R3", "Bounded", "+ knowing what,\nwhich rule", "5 of 7"),
          ("R4", "Accountable", "+ cost, where,\nintegrity", "7 of 7")]


def conformance_levels():
    """Figure 2.3. Each level adds sections; R4 answers all seven."""
    body, base, w = [], 214, 110
    for i, (code, name, adds, answers) in enumerate(LEVELS):
        x, y = 4 + i * (w + 4), 84 - i * 26
        body += [box(x, y, w, base - y, fill=[
                     "#ffffff", PALE, "#dcdcdc", FILL][i]),
                 text(x + 8, y + 18, f"{code} {name}", size=12.5,
                      weight=700),
                 text(x + 8, y + 36, adds, size=11.5),
                 text(x + 8, y + 70 if "\n" in adds else y + 56,
                      f"answers {answers}", size=11.5, italic=True)]
    body += [agent(12, 168, 94, 36, "Night Owl\n$85 refund", kind="shadow",
                   size=11.5),
             agent(348, 168, 104, 36, "Speedy\n$40 refund", size=11.5),
             arrow([(4, 228), (452, 228)]),
             text(228, 248, "each level requires the ones below it",
                  size=11.5, italic=True, anchor="middle", fill=MID)]
    return svg(256, body)


def hash_chain():
    """Figure 2.4. Append, never edit: each record commits to the last."""
    body = [box(4, 30, 74, 46, fill=PALE),
            text(41, 50, "genesis", size=11.5, weight=700, anchor="middle"),
            text(41, 66, "sha256:0…0", size=11.5, mono=True,
                 anchor="middle")]
    records = [("01 lookup", "R4"), ("02 refund", "R4"),
               ("03 outcome", "+7 days")]
    for i, (name, note) in enumerate(records):
        x = 112 + i * 118
        body += [receipt(x, 22, 92, 64),
                 text(x + 46, 44, name, size=12, weight=700,
                      anchor="middle"),
                 text(x + 46, 60, note, size=11.5, anchor="middle"),
                 text(x + 46, 76, "hash", size=11.5, mono=True,
                      anchor="middle", fill=MID)]
        prev_x = 78 if i == 0 else x - 26
        body.append(arrow([(x - 2, 54), (prev_x + 2, 54)]))
    body += [text(4, 12, "Each arrow is a prev_hash: every record "
                  "points back at the one before it.", size=11.5,
                  italic=True),
             receipt(230, 118, 92, 64, fill=PALE),
             text(276, 140, "02 altered", size=12, weight=700,
                  anchor="middle"),
             text(276, 156, "$40 → $400", size=11.5, anchor="middle"),
             line([(276, 92), (276, 116)], dash="3 3"),
             text(8, 134, "Alter 02, and its own hash\nno longer "
                  "matches. Rehash it,\nand 03 no longer points at it.",
                  size=11.5),
             receipt(4, 212, 92, 52, fill="#ffffff"),
             text(50, 234, "04 Night Owl", size=11.5, weight=700,
                  anchor="middle"),
             text(50, 250, "R1, unchained", size=11.5, anchor="middle"),
             text(112, 236, "R1 to R3 receipts may sit outside the chain.",
                  size=11.5),
             text(112, 252, "Only R4 requires integrity.", size=11.5)]
    return svg(274, body)


FIGURES = {"fig-2-1-receipt-strip": receipt_strip,
           "fig-2-2-receipt-anatomy": receipt_anatomy,
           "fig-2-3-conformance-levels": conformance_levels,
           "fig-2-4-hash-chain": hash_chain}

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        (out / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print("wrote", out / f"{name}.svg")
