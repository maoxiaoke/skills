---
name: extract-design
description: Extract and normalize an existing design system from a local codebase, one or more live webpages, or both, then write a Google Stitch-inspired, Tailwind-exportable design-system.toml. Use when the user asks to extract, reverse-engineer, document, normalize, or reconstruct design tokens, typography roles, spacing, colors, icons, radii, shadows, breakpoints, motion, or evidence-backed component tokens from an implemented product. Do not use to invent a new visual identity, redesign an interface, or generate UI components from a design system.
---

# Extract Design

Produce one normalized `design-system.toml` from implemented sources. Treat the
codebase as the declared system and rendered webpages as runtime verification.
Model the machine-readable token layer of the Google Stitch DESIGN.md
specification in TOML; do not generate its Markdown rationale layer unless the
user explicitly requests a `DESIGN.md` document.

## Inputs

Resolve these from the request and workspace before asking questions:

- A local repository or application directory.
- One or more webpage URLs, when available.
- An optional output path. Default to `design-system.toml` in the repository
  root, or the current directory when no repository is supplied.

The skill works with either source alone, but inspect both whenever both are
provided. Confirm that the repository and webpage appear to represent the same
product; report a likely version or product mismatch instead of silently
combining unrelated values.

## Output contract

Start new outputs from [assets/design-system.toml](assets/design-system.toml).
Populate only values supported by the inspected sources.

- Keep the Stitch-inspired core groups: `colors`, `typography`, `rounded`,
  `spacing`, and optional `components`.
- Keep framework-neutral token names. Use the deterministic Tailwind mapping in
  the asset header instead of duplicating every value as a `--token` key.
- Keep examples as TOML comments.
- Leave unknown values empty; never complete a scale by guessing.
- Preserve valid source-specific tokens under `[extensions]`; unknown names are
  allowed when their values satisfy the corresponding token type.
- Do not add evidence, confidence, or audit-log sections. Add component tokens
  only when repeated implementation evidence supports them.
- Use rem for scalable dimensions and px for fixed dimensions according to
  [references/normalization.md](references/normalization.md).
- If the output already exists, inspect and preserve intentional user content.
  Do not replace it wholesale without explicit authorization.

## Workflow

### 1. Establish scope

Identify the repository root, relevant app/package in a monorepo, webpage URLs,
default theme, and output path. Prefer discovered facts over questions. State
any assumption that changes which app or theme will be inspected.

### 2. Inspect the codebase

Follow the codebase procedure in
[references/source-inspection.md](references/source-inspection.md). Use `rg` and
`rg --files` first. Inspect configuration and source definitions before broad
searches or generated output. Do not read vendored dependencies or build
artifacts unless they are the only available runtime evidence.

Collect candidates for:

- Font families, files, loading strategy, weights, sizes, line heights, and
  tracking.
- Semantic colors and raw palettes.
- Spacing, radius, shadow, breakpoint, container, and motion scales.
- Icon library, package, rendering format, sizes, stroke, fill, and color.
- Semantic typography roles and repeated component property tokens.
- Interaction variants, grid/page layout, and output targets.

### 3. Inspect webpages

When a webpage is in scope, invoke the available ego-browser skill and use
ego-lite first. Fall back to another browser or fetch mechanism only when
ego-lite cannot access the required page or data.

Inspect the rendered DOM and computed styles, not screenshots alone. Sample the
smallest representative set of pages that covers the shell, content, controls,
and dense/product UI. Follow the webpage procedure in
[references/source-inspection.md](references/source-inspection.md).

Use screenshots only to confirm visual roles or investigate values that the DOM
does not explain. Do not expose cookies, tokens, private headers, or other
session secrets in the output or handoff.

### 4. Reconcile and normalize

Apply [references/normalization.md](references/normalization.md). Rank evidence
in this order:

1. Explicit design-token or theme configuration in the target repository.
2. CSS custom properties, font declarations, and package/import declarations.
3. Repeated computed values across representative rendered pages.
4. Repeated literals in component styles.
5. Visual inference from screenshots.

Use webpage evidence to verify what is actually active. If runtime values
conflict with declared values, do not average them. Select the value belonging
to the requested environment/theme and mention the conflict in the handoff.

### 5. Write the TOML

For a new output, reproduce the asset template and replace empty values with
normalized facts. For an existing output, make focused edits.

Preserve valid source names under `[extensions]` when they are useful, but use
semantic names in the canonical groups. Keep one canonical value for each
token and reuse it with `{path.to.token}` references. For a rem value, include
its px equivalent as an inline comment when useful; the `[units]` table remains
the machine-readable conversion contract.

### 6. Validate and hand off

Resolve the installed skill directory from this `SKILL.md`, then run:

```bash
python3 /absolute/path/to/extract-design/scripts/validate_design_system.py /absolute/path/to/design-system.toml
python3 /Users/nazha/.agents/skills/skill-creator/scripts/quick_validate.py /absolute/path/to/extract-design
```

Resolve structural errors before finishing. Warnings for empty values are an
extraction coverage report, not a reason to invent missing tokens.

Report:

- The exact output path.
- Repository path and inspected URLs.
- Populated and missing token groups.
- Any repository/runtime conflicts or source limitations.
- Validation results.
