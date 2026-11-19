#!/bin/sh
# Renders one chapter's figures: python -> SVG -> 300 DPI grayscale
# PNG. Usage, from agent-observability-book/: sh figures/render.sh 08
set -e
python -m "figures.chapter$1" figures/svg
mkdir -p figures/png
n=$(echo "$1" | sed 's/^0//')
for f in figures/svg/fig-"$n"-*.svg; do
  png="figures/png/$(basename "$f" .svg).png"
  rsvg-convert -d 300 -p 300 "$f" -o "$png"
  convert "$png" -background white -alpha remove -colorspace Gray \
    -depth 8 -strip -define png:include-chunk=pHYs \
    -units PixelsPerInch -density 300 "$png"
  echo "rendered $png"
done
