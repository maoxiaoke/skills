# Source inspection

Use this procedure to gather design facts before normalization. Keep an
internal candidate list while working; do not add provenance records to the
final TOML.

## Contents

- [Codebase](#codebase)
- [Webpages](#webpages)
- [Cross-source reconciliation](#cross-source-reconciliation)

## Codebase

### Locate the implemented design system

Start at the requested repository or app root. In a monorepo, resolve the exact
package before reading sibling applications.

Use `rg --files` to locate the highest-signal sources:

- `package.json`, lockfiles, framework configuration, and workspace manifests.
- `tailwind.config.*`, Tailwind v4 CSS entrypoints, PostCSS configuration, and
  theme or token files.
- Global CSS, CSS modules, Sass/Less variables, CSS-in-JS themes, and component
  variant definitions.
- Font files and `@font-face` declarations.
- Icon packages, imports, SVG sprites, and shared icon wrappers.
- Media/container queries, keyframes, transition utilities, and layout shells.

Exclude `.git`, `node_modules`, dependency caches, generated bundles, coverage,
and build output from initial searches. Inspect them only when source files are
unavailable and say so in the handoff.

### Extract declared facts

Prefer exact definitions over usage frequency:

1. Read token/theme files and global CSS variables.
2. Read Tailwind configuration or Tailwind v4 `@theme` blocks.
3. Check package manifests and imports for font and icon libraries.
4. Trace aliases until they resolve to concrete values.
5. Search component styles for repeated values and interaction states.
6. Check breakpoints, containers, page padding, grid columns, and gutters in
   layout primitives.

Record theme context for every candidate. Do not merge light and dark values
into one default-theme token.

### Detect fonts and icons

For fonts, distinguish the declared family stack from the loading source.
Capture sans, mono, and optional serif stacks, weight availability,
`font-display`, and whether assets are hosted, self-hosted, or system-only.

For icons, prefer package/import evidence. Capture the library and package,
outline or filled style, SVG/component/sprite format, default and supported
sizes, stroke width, line cap/join, fill, and `currentColor` behavior. Do not
identify an icon library from visual resemblance alone.

## Webpages

### Open with ego-lite

Use ego-lite through the ego-browser skill for navigation and inspection. Reuse
the user's existing authenticated session only when the requested page requires
it. Never copy authentication material into notes or output.

Start with the provided URL. Follow same-product navigation only as needed. A
typical representative set is:

- One shell or landing page for global color, typography, and navigation.
- One content-heavy page for text hierarchy and content width.
- One control- or data-heavy page for spacing, states, density, and icons.

One page is enough when it already covers these roles. Avoid crawling the whole
site.

### Inspect runtime values

Prefer CSS custom properties and loaded stylesheets, then sample computed styles
from representative elements:

- `html`, `body`, headings, paragraphs, labels, captions, links, and code.
- Primary, secondary, destructive, icon-only, and disabled controls.
- Inputs, selects, cards, menus, dialogs, tables, tabs, badges, and tooltips.
- Page shell, content container, grid, section, and stacked layouts.

Capture these computed properties where relevant:

- `font-family`, `font-size`, `font-weight`, `line-height`, `letter-spacing`.
- Text/background/border colors and opacity.
- Padding, margin, gap, width/max-width, and responsive changes.
- Border width/radius, box shadow, and focus ring.
- Transition property/duration/timing and animation name/duration.
- SVG dimensions, stroke width, line cap/join, fill, and color.

Use `document.fonts` or equivalent browser data to distinguish requested fonts
from fonts that actually loaded. Inspect CSS variables on the root/theme scope
and resolve aliases when computed values are needed.

### Responsive and interaction sampling

If the site is responsive, compare at least one compact and one wide viewport.
Infer a breakpoint only when a layout change can be bracketed or its media query
is visible in CSS. Do not derive the entire breakpoint scale from device names.

Inspect hover, focus-visible, active, selected, disabled, loading, and open
states when they can be reached safely. Do not submit destructive forms or
mutate production data merely to expose a style.

## Cross-source reconciliation

Compare code and webpage candidates before writing:

- Matching variable names and values strongly confirm a token.
- A declared but unused token still belongs to the codebase's system; a runtime
  value confirms whether it is active on sampled pages.
- A computed value with no declared token may be normalized when it repeats or
  clearly owns a semantic role.
- A one-off literal should not become a global scale token without repeated use
  or an explicit semantic role.
- A code/runtime mismatch may indicate a deployment/version difference. Keep
  the requested environment authoritative and report the discrepancy.
