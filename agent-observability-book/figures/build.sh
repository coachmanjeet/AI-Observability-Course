#!/bin/sh
# Rebuilds every print figure: Python -> SVG -> 300 DPI grayscale PNG.
# Run from agent-observability-book/. Needs rsvg-convert and ImageMagick.
set -e
for chapter in figures/chapter*.py; do
  python -m "figures.$(basename "$chapter" .py)" figures/svg
done
mkdir -p figures/png
for f in figures/svg/*.svg; do
  png="figures/png/$(basename "$f" .svg).png"
  rsvg-convert -d 300 -p 300 "$f" -o "$png"
  # 8-bit grayscale, no color profile, 300 DPI recorded in the file
  convert "$png" -background white -alpha remove -colorspace Gray \
    -depth 8 -strip -define png:include-chunk=pHYs \
    -units PixelsPerInch -density 300 "$png"
  echo "rendered $png"
done
