# PNG Export

Convert any skill-generated SVG to PNG with the bundled zero-install renderer:

```bash
node scripts/svg2png.mjs <input.svg> <output.png> [width]
```

- `width` defaults to 2160 (2x of the standard 1080 viewBox). Use 3240 for print/retina-zoom contexts.
- Requires any JS runtime — the same command runs under `bun` or `deno run --allow-read --allow-write --allow-net` unchanged.
- No npm install, no network for skill-generated diagrams: the renderer (resvg-wasm) and the three brand font families (Geist, Geist Mono, Instrument Serif — static weights 400/500/600) are vendored in `scripts/`.

## Font resolution

Families referenced by the SVG resolve through a ladder, each step reported on stderr:

1. **vendor** — the three brand families, always loaded, zero network
2. **cache** — `~/.cache/diagram-fonts/<family>/`, populated by step 4
3. **system** — fuzzy filename match against OS font directories
4. **google fonts** — downloaded as static per-weight ttf (legacy-UA css2 trick), written to cache

An unresolvable family logs `WARN: ... falling back to Geist` and rendering continues — there is no silent text drop. If the SVG contains CJK characters, a system CJK font is auto-loaded as a glyph safety net.

## Known limits — check these before debugging a "wrong" PNG

| Symptom | Cause | What to do |
|---|---|---|
| Mixed CJK/Latin label renders entirely in the CJK font (Latin part loses brand font) | resvg fallback granularity is the whole text chunk, not per character — different from browsers | Expected behavior. Pure-CJK and pure-Latin labels are unaffected. If brand fidelity matters, keep Latin and CJK in separate `<text>` elements |
| All weights render identical (600 looks like 400) | A variable font (`Name[wght].ttf`) reached fontdb — it only exposes the default instance | Use static per-weight files. The Google Fonts tier already returns statics; only manually-added fonts can hit this |
| Custom font ignored despite being available as woff/woff2 | fontdb only parses ttf/otf/ttc | Provide a ttf/otf, or let the Google tier fetch it |
| Text missing entirely | Family unresolved AND default font broken | Check stderr report; verify `scripts/fonts/` is intact (8 files) |
| Output blurry in target context | Exported at 1x | Re-export with a larger width argument |

## What the renderer does not support

`<foreignObject>`, `<script>`, CSS animations, external images — none are used by skill-generated SVGs (§11 output rules). External SVGs using them will render with those elements missing.
