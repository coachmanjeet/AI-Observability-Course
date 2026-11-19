"""The book's figure notation, as code (legend printed in Chapter 3).

Every figure is drawn in grayscale for a black-and-white print interior.
Meaning comes from shape and line style, never color:

  agents      rounded box: solid for 1P, dashed for 3P, dotted for shadow
  tools, MCP  tabbed box
  policy gate diamond
  data store  cylinder
  receipt     document with a torn bottom edge
  boundary    dashed container
  flows       solid arrow with a filled head for calls,
              thin arrow with an open head for trace context

Units: 100 per inch. Figures are 4.6 in wide to fit the 6 x 9 in text
block, and text is never smaller than 11.5 units (8.3 pt in print).
"""
from xml.sax.saxutils import escape

INK, MID, FILL, PALE = "#000000", "#4d4d4d", "#c8c8c8", "#ececec"
SANS = "Inter, 'DejaVu Sans', sans-serif"
MONO = "'DejaVu Sans Mono', monospace"
WIDTH = 460
LINE, THIN, BOLD_LINE = 1.4, 1.0, 2.2
DASH, DOT = "6 3.5", "1.6 2.6"


def svg(height, body, width=WIDTH):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width / 100}in" height="{height / 100}in" '
            f'viewBox="0 0 {width} {height}">\n'
            f'<defs>{_markers()}</defs>\n'
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>\n'
            + "\n".join(body) + "\n</svg>\n")


def _markers():
    return ('<marker id="call" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
            '<marker id="trace" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M1,1 L9,5 L1,9" fill="none" stroke="{INK}" '
            'stroke-width="1.3"/></marker>')


def text(x, y, s, size=12, weight=400, anchor="start", mono=False,
         italic=False, fill=INK):
    """One or more lines of text; '\n' starts a new line."""
    family = MONO if mono else SANS
    style = ' font-style="italic"' if italic else ""
    out = []
    for i, line in enumerate(str(s).split("\n")):
        out.append(f'<text x="{x}" y="{y + i * size * 1.22:.1f}" '
                   f'font-family="{family}" font-size="{size}" '
                   f'font-weight="{weight}" text-anchor="{anchor}"'
                   f'{style} fill="{fill}">{escape(line)}</text>')
    return "\n".join(out)


def _stroke(kind):
    dash = {"3P": DASH, "shadow": DOT, "boundary": DASH}.get(kind)
    return f' stroke-dasharray="{dash}"' if dash else ""


def box(x, y, w, h, fill="#ffffff", r=0, width=LINE, kind=None):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
            f'fill="{fill}" stroke="{INK}" stroke-width="{width}"'
            f'{_stroke(kind)}/>')


def agent(x, y, w, h, label, kind="1P", fill="#ffffff", size=12,
          weight=600):
    """Rounded box. kind is 1P (solid), 3P (dashed) or shadow (dotted)."""
    line = BOLD_LINE if kind == "shadow" else LINE
    return "\n".join([
        box(x, y, w, h, fill=fill, r=9, width=line, kind=kind),
        _centered(x + w / 2, y, h, label, size, weight)])


def tool(x, y, w, h, label, fill="#ffffff", size=12):
    """Tabbed box: a tool, MCP server or API."""
    tab = (f'<path d="M{x},{y + 1} v-7 h{min(28, w / 3)} v7" '
           f'fill="{fill}" stroke="{INK}" stroke-width="{LINE}"/>')
    return "\n".join([tab, box(x, y, w, h, fill=fill),
                      _centered(x + w / 2, y, h, label, size)])


def gate(cx, cy, r, label="", size=11.5, fill="#ffffff"):
    """Diamond: a policy decision or enforcement point."""
    pts = f"{cx},{cy - r} {cx + r},{cy} {cx},{cy + r} {cx - r},{cy}"
    out = [f'<polygon points="{pts}" fill="{fill}" stroke="{INK}" '
           f'stroke-width="{LINE}"/>']
    if label:
        out.append(_centered(cx, cy - r, 2 * r, label, size, 600))
    return "\n".join(out)


def store(x, y, w, h, label, fill="#ffffff", size=12):
    """Cylinder: a data store, registry or ledger."""
    e = 5
    body = (f'<path d="M{x},{y + e} v{h - 2 * e} '
            f'a{w / 2},{e} 0 0 0 {w},0 v-{h - 2 * e}" fill="{fill}" '
            f'stroke="{INK}" stroke-width="{LINE}"/>')
    top = (f'<ellipse cx="{x + w / 2}" cy="{y + e}" rx="{w / 2}" ry="{e}" '
           f'fill="{fill}" stroke="{INK}" stroke-width="{LINE}"/>')
    return "\n".join([body, top, _centered(x + w / 2, y + 2 * e,
                                            h - 2 * e, label, size)])


def receipt(x, y, w, h, fill="#ffffff", width=LINE):
    """Document with a torn bottom edge: an Agent Receipt."""
    teeth = max(4, int(w // 12))
    step = w / teeth
    zig = " ".join(f"L{x + w - (i + 0.5) * step:.1f},{y + h - 6} "
                   f"L{x + w - (i + 1) * step:.1f},{y + h}"
                   for i in range(teeth))
    return (f'<path d="M{x},{y} H{x + w} V{y + h} {zig} Z" fill="{fill}" '
            f'stroke="{INK}" stroke-width="{width}" '
            'stroke-linejoin="round"/>')


def boundary(x, y, w, h, label="", size=11.5):
    out = [box(x, y, w, h, fill="none", r=4, width=THIN + 0.2,
               kind="boundary")]
    if label:
        out.append(text(x + 6, y + 14, label, size=size, italic=True))
    return "\n".join(out)


def arrow(points, kind="call", both=False, dash=None):
    """Polyline arrow. kind 'call' is solid and heavy; 'trace' is thin.
    dash draws a span link: context recorded, not inherited."""
    d = "M" + " L".join(f"{px},{py}" for px, py in points)
    marker = "call" if kind == "call" else "trace"
    width = LINE + 0.2 if kind == "call" else THIN + 0.2
    start = f' marker-start="url(#{marker})"' if both else ""
    dashed = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{d}" fill="none" stroke="{INK}" '
            f'stroke-width="{width}"{dashed}{start} '
            f'marker-end="url(#{marker})"/>')


def line(points, width=LINE, dash=None, color=INK):
    d = "M" + " L".join(f"{px},{py}" for px, py in points)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{d}" fill="none" stroke="{color}" '
            f'stroke-width="{width}"{extra}/>')


def badge(cx, cy, s, size=11.5):
    """Small black disc with white text: chapter or callout numbers."""
    r = size * 0.85 if len(s) < 3 else size * 1.05
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{INK}"/>'
            f'<text x="{cx}" y="{cy + size * 0.36}" font-family="{SANS}" '
            f'font-size="{size}" font-weight="700" text-anchor="middle" '
            f'fill="#ffffff">{escape(s)}</text>')


def _centered(cx, top, h, label, size, weight=400):
    lines = str(label).split("\n")
    first = top + h / 2 - (len(lines) - 1) * size * 0.61 + size * 0.36
    return text(cx, first, label, size=size, weight=weight,
                anchor="middle")
