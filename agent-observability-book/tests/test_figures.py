"""Print rules for every figure: grayscale, 4.6 in wide, text >= 8 pt."""
import importlib
import pathlib
import pkgutil
import re
import xml.etree.ElementTree as ET

import pytest

import figures
from figures import chapter02, chapter03

# Every figures/chapterNN.py but 02 and 03 exports FIGURES.
LATER = [importlib.import_module(f"figures.{m.name}")
         for m in pkgutil.iter_modules(figures.__path__)
         if re.fullmatch(r"chapter\d\d", m.name)
         and int(m.name[-2:]) not in (2, 3)]

FLEET = pathlib.Path(__file__).parent.parent / "maturity" / "fleet.json"

FIGURES = {**{name: draw() for name, draw in chapter02.FIGURES.items()},
           "fig-3-1": chapter02.receipt_strip(highlight={0, 3}),
           "fig-3-2": chapter03.discover_govern_observe(),
           "fig-3-3": chapter03.reference_architecture(),
           "fig-3-4": chapter03.maturity_ladder(FLEET),
           "fig-3-5": chapter03.legend(),
           **{name: draw() for module in LATER
              for name, draw in module.FIGURES.items()}}


@pytest.mark.parametrize("name", FIGURES)
def test_figure_meets_print_rules(name):
    svg = FIGURES[name]
    root = ET.fromstring(svg)
    assert root.get("width") == "4.6in"
    sizes = [float(s) for s in re.findall(r'font-size="([\d.]+)"', svg)]
    assert sizes and min(sizes) >= 11.5            # 8.3 pt at print size
    for color in re.findall(r'#([0-9a-fA-F]{6})', svg):
        r, g, b = color[:2], color[2:4], color[4:]
        assert r == g == b, f"{name} uses a non-gray color #{color}"
