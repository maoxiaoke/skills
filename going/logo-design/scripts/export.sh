#!/usr/bin/env bash
set -euo pipefail

# Usage: export.sh <input.svg> <output-dir>
# Exports an SVG to PNG at standard logo sizes using the vendored resvg-wasm
# renderer (scripts/svg2png.mjs). Zero-install: no external converter, no
# package manager, no network for the render itself. Needs only a JS runtime.

INPUT_SVG="${1:?Usage: export.sh <input.svg> <output-dir>}"
OUTPUT_DIR="${2:?Usage: export.sh <input.svg> <output-dir>}"
SIZES=(16 32 48 192 512 1024 2048)
BASENAME="logo"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SVG2PNG="$HERE/svg2png.mjs"

# Pick a JS runtime — svg2png.mjs runs unchanged under node / bun / deno.
RUNTIME=""
if command -v node &>/dev/null; then
  RUNTIME="node"
elif command -v bun &>/dev/null; then
  RUNTIME="bun"
elif command -v deno &>/dev/null; then
  RUNTIME="deno run --allow-read --allow-write --allow-net"
else
  echo "ERROR: No JavaScript runtime found (need node, bun, or deno)."
  echo "Install Node.js: https://nodejs.org"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Copy SVG to output
cp "$INPUT_SVG" "$OUTPUT_DIR/$BASENAME.svg"

echo "Using: resvg-wasm via $RUNTIME"
echo ""

for SIZE in "${SIZES[@]}"; do
  OUTPUT="$OUTPUT_DIR/${BASENAME}-${SIZE}.png"
  $RUNTIME "$SVG2PNG" "$INPUT_SVG" "$OUTPUT" "$SIZE"
  echo "  Exported: ${BASENAME}-${SIZE}.png (width ${SIZE}px)"
done

echo ""
echo "Done. Files in: $OUTPUT_DIR"
