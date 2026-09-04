# Normalization rules

Map extracted facts into `assets/design-system.toml`. The schema is a TOML
translation of the machine-readable layer in the Google Stitch DESIGN.md
specification, extended for icons, responsive layout, shadows, motion, and
Tailwind export.

## Contents

- [Core model](#core-model)
- [Token types](#token-types)
- [Units](#units)
- [Group mapping](#group-mapping)
- [Tailwind export](#tailwind-export)
- [Unknown content](#unknown-content)

## Core model

Use these Stitch-compatible groups as the normative layer:

- Top-level `version`, `name`, and optional `description`.
- `[colors]`: a flat map of semantic or palette names to sRGB hex colors.
- `[typography.<role>]`: composite typography tokens.
- `[rounded]`: named corner-radius dimensions.
- `[spacing]`: named dimensions or unitless layout values.
- `[components.<name>]`: optional component property tokens and variants.

Use `[fonts]`, `[icons]`, `[breakpoints]`, `[containers]`, `[shadows]`,
`[motion]`, `[layout]`, `[variants]`, and `[implementation]` as open extensions.
Preserve additional source-specific facts under `[extensions]` instead of
forcing them into an unrelated canonical group.

Populate only values supported by code or rendered evidence. Do not fill a
scale for visual neatness. Keep the default theme in the canonical groups;
record available theme names under `[metadata]` without mixing theme values.

## Token types

### Color

Normalize colors to sRGB hex strings. Use six digits for opaque colors and
eight digits when alpha is required:

```toml
primary = "#2563EB"
overlay = "#0F172A8F"
```

Do not convert a token reference into a duplicated literal. Keep the reference.

### Dimension

A dimension is a number followed by `px`, `em`, or `rem`. Zero may be written
as `0` or `0px`. Preserve CSS functions only in open extension groups where the
implemented system genuinely depends on them; they are outside the Stitch core
dimension type.

### Typography

Each `[typography.<role>]` table may contain:

- `fontFamily`: string or reference to a primitive such as `{fonts.sans}`.
- `fontSize`: Dimension.
- `fontWeight`: numeric weight or a token reference.
- `lineHeight`: Dimension or unitless multiplier; prefer unitless when that is
  how the source behaves.
- `letterSpacing`: Dimension.
- `fontFeature`: `font-feature-settings` string.
- `fontVariation`: `font-variation-settings` string.

Prefer semantic roles such as `headline-display`, `headline-lg`, `headline-md`,
`body-lg`, `body-md`, `body-sm`, `label-lg`, `label-md`, and `label-sm`. Retain
`code-md` when a monospace product role exists. Unknown role names are valid;
do not force distinctive source roles into an inaccurate standard name.

### Token reference

Write references as `{path.to.token}`:

```toml
fontFamily = "{fonts.sans}"
backgroundColor = "{colors.primary}"
rounded = "{rounded.md}"
```

Outside `[components]`, references must resolve to primitive values. Component
properties may reference a composite typography token such as
`{typography.label-lg}`. Never create dangling references.

## Units

Use `[units]` as the rem/px conversion contract:

```toml
[units]
rootFontSizePx = 16
scalableUnit = "rem"
fixedUnit = "px"
outputs = ["rem", "px"]
```

Set `rootFontSizePx` from the implemented or computed root size. Retain 16 only
when the product uses the browser default or no contrary value exists.

Use rem for typography, spacing, ordinary radii, breakpoints, and containers.
When the source is px, divide by `rootFontSizePx`, use a concise rem decimal,
and retain the px equivalent in an inline comment:

```toml
fontSize = "1rem" # 16px
section = "3rem" # 48px
```

Keep px for icons, strokes, hairlines, raster-aligned details, and intentionally
fixed values. Do not create duplicate `-px` token names. Non-Tailwind web apps
can consume rem and CSS variables directly; px-only consumers can resolve them
using `rootFontSizePx`.

## Group mapping

### Fonts and icons

Use `[fonts]` for sans, mono, and optional serif family primitives plus source
and loading metadata. Use the computed body family for `fonts.sans` and the
code/preformatted family for `fonts.mono`.

Use `[icons]` for one primary icon system. Identify it from packages, imports,
or shared SVG infrastructure, never from visual resemblance. If multiple icon
systems are intentional, preserve secondary systems under `[extensions]`.

### Colors

Map page canvas and text to `background` and `foreground`; raised regions to
`surface` and `on-surface`; low-emphasis roles to `muted` and `on-muted`;
dividers and outlines to `border`; focus indication to `ring`; the main action
to `primary`; supporting actions to `secondary` or `tertiary`; and status roles
to `info`, `success`, `warning`, and `error`.

Use `on-*` for foreground colors placed on semantic fills. Add hover and active
tokens only when those states exist. Keep raw palette steps in the same flat
map, for example `neutral-50` or `primary-60`.

### Spacing, shape, and layout

Use `spacing.base` only when an explicit or strongly repeated base step exists.
Sort repeated spacing and radius values into real source levels; leave unused
template levels empty. Keep `rounded.full` for an authored pill/circle value.

Use `[layout]` for structural column counts, gutters, margins, and page padding.
Prefer references such as `{spacing.gutter}` instead of repeating literals.
Use `[breakpoints]` and `[containers]` for exact authored thresholds and width
limits; do not infer exact values from screenshots alone.

### Elevation and motion

Use `[shadows]` for reusable full shadow strings, including multiple layers.
When the product is flat, keep shadows empty rather than inventing elevation;
the extracted design summary can state that depth comes from borders or tonal
layers.

Use `[motion]` for reusable `ease-*` and `animate-*` tokens. Do not promote an
isolated component transition into the global motion system.

### Components and variants

Add `[components.<name>]` only for recurring component atoms with stable shared
properties. Supported Stitch properties are `backgroundColor`, `textColor`,
`typography`, `rounded`, `padding`, `size`, `height`, and `width`. Preserve an
unknown property with a validation warning when it is genuinely part of the
source system.

Represent a component state as a related entry, for example
`components.button-primary-hover`, rather than embedding an undocumented state
object. Keep `[variants]` only for the implementation's selector mechanisms.

## Tailwind export

Keep the TOML framework-neutral. Map names deterministically during export:

- `fonts.sans` -> `--font-sans`
- `colors.primary` -> `--color-primary`
- `typography.body-md.fontSize` -> `--text-body-md`
- `typography.body-md.lineHeight` -> `--text-body-md--line-height`
- `spacing.sm` -> `--spacing-sm`; `spacing.base` may become `--spacing`
- `rounded.md` -> `--radius-md`
- `breakpoints.md` -> `--breakpoint-md`
- `containers.content` -> `--container-content`
- `shadows.sm` -> `--shadow-sm`
- `motion.ease-standard` -> `--ease-standard`
- `motion.animate-fade-in` -> `--animate-fade-in`

References remain canonical in TOML and are resolved when producing CSS or a
Tailwind `@theme` block. Do not duplicate every value in a second Tailwind table.

## Unknown content

Follow Stitch's extensibility rule: preserve unknown token names and extension
tables when their values are valid. Warn for unknown component properties. A
duplicate TOML table or key is invalid and must be rejected by parsing.
