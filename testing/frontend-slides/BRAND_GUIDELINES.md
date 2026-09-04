# SAVANA Brand Guidelines (Slide Design Tokens)

Distilled from the SAVANA Brand Bible 2026 for presentation generation. When Brand Mode is active (see SKILL.md), these rules **override** the generic Design Aesthetics guidance — brand consistency beats visual novelty.

## Official Color Palette

| Token | Name | Hex | Role | Use for |
| --- | --- | --- | --- | --- |
| `--sv-yellow` | Sunshine Yellow | `#FEC200` | Primary / core brand | Cover backgrounds, CTA, emphasis, highlight tags |
| `--sv-blue` | Midnight Blue | `#305492` | Secondary / calm | Section backgrounds, charts, info blocks |
| `--sv-terra` | Terra Cotta | `#EF725E` | Warm accent | Emotional content, alerts, key markers |
| `--sv-pink` | Bubblegum Pink | `#FE7B9B` | Energy accent | Playful scenes, feminine content |
| `--sv-green` | Patina Green | `#5DA58B` | Nature accent | Sustainability, Modest series |
| `--sv-candy` | Cotton Candy | `#F4C3CD` | Soft accent | Background washes, soft transitions |
| `--sv-lemon` | Pale Lemon | `#FBF6B2` | Light accent | Secondary backgrounds, info cards |

**WCAG-safe pairings (use ONLY these text/background combos):**

| Background | Text | Contrast | Grade |
| --- | --- | --- | --- |
| `#FEC200` | `#000000` | 16.8:1 | AAA — safest brand combo |
| `#305492` | `#FEC200` | 4.6:1 | AA — core brand combo |
| `#305492` | `#FFFFFF` | 7.2:1 | AAA |
| `#EF725E` | `#FFFFFF` | 3.8:1 | AA Large — headlines ≥ 24px only |
| `#5DA58B` | `#FFFFFF` | 4.9:1 | AA |
| `#FFFFFF` | `#000000` | 21:1 | AAA — default body layout |
| `#000000` | `#FEC200` | 16.8:1 | AAA — promo / high emphasis |

**Pairing taboos:** never place Sunshine Yellow next to Terra Cotta in large areas; never mix Terra Cotta with Bubblegum Pink; never place Patina Green adjacent to Cotton Candy; never use Pale Lemon on white (too low contrast); never use Midnight Blue as a large body-text background block behind long paragraphs.

## Typography

Load from Google Fonts: **Montserrat** (600, 700, 800, 900) + **Poppins** (400).
Brand Mode overrides the skill's "avoid common fonts" rule — these two families are mandatory.

| Level | Font / Weight | Size (1920×1080 stage) | Line height | Letter spacing | Use |
| --- | --- | --- | --- | --- | --- |
| Display Hero | Montserrat Black 900 | 150–230px | 0.85 | -0.03em | Cover brand name, section heroes |
| Display Large | Montserrat ExtraBold 800 | 115–150px | 0.90 | -0.02em | Section titles |
| H1 | Montserrat Bold 700 | 48–64px | 1.0 | -0.01em | Slide titles |
| H2 | Montserrat Bold 700 | 32–40px | 1.1 | 0 | Sub-blocks |
| Label | Montserrat SemiBold 600 | 12–14px | 1.4 | 0.15em | Tags, numbering, categories |
| Body Large | Poppins 400 | 18–20px | 1.6 | 0 | Lead paragraphs |
| Body | Poppins 400 | 14–16px | 1.5 | 0 | Body text, lists |
| Caption | Poppins 400 | 12px | 1.4 | 0.02em | Footnotes, sources |

(Display sizes converted from the bible's 8–12vw / 6–8vw to the fixed 1920px stage.)

## Logo

Source: [assets/logo.svg](assets/logo.svg) — the lowercase "savana" wordmark as a single-path SVG (800×198 viewBox, filled `#FEC200`).

**Embedding:** inline the SVG into the HTML and recolor via CSS `fill` to one of the three approved variants:

- Black wordmark on white / light backgrounds
- White wordmark on Midnight Blue
- Black wordmark on Sunshine Yellow

**Placement rules (non-negotiable):**

- Fixed position **bottom-left** of every slide, inside the 1920×1080 stage
- Minimum height 24px; on the 1920×1080 stage use ~40px height for comfortable legibility
- Clear space: at least 1× letter height of padding on all sides
- Never stretch, rotate, skew, add shadows/strokes/gradients, change case, or place on busy or low-contrast backgrounds

## Voice for Slide Copy

Tone: **joyful, quirky, smart.** Sentence case everywhere (no ALL-CAPS body copy; caps allowed only for Montserrat display/label styling per the type scale).

- Lead with the result: "A cleaner line from desk to dinner." — not hype ("Ultimate elevated vibe")
- Style-function language: "Breathes better in heat." — not "Insane." / "Magic." / "Life-changing."
- Encourage, don't judge: never "perfect for problem areas" / body-fixing language
- Banned words (never render in any deck): cheap, poor, lower-class, class ascent, developing-country women, skinny, fat, hide flaws, fix your body, must-have, obsessed, insane, crazy hot, slutty, modest-only, ethnic vibe, exotic, affordable luxury, quiet luxury
- Preferred words: current, sharp, wearable, lighter, easier, cleaner, breathable, polished, ready, confidence, repeat wear

## Fixed Elements

- Closing slide footer: `© 2026 SAVANA. All rights reserved.`
- External slogan available for covers/closings: _"Dress the Best Version of You."_
- Brand promise line: _"See it. Wear it. Own your version."_

## Visual Direction (for backgrounds & imagery)

High-contrast, directional light with real shadow depth — never flat, even, front-lit "studio white." When building CSS-generated atmosphere, prefer bold color-blocked panels from the official palette, strong diagonals, and deep shadows over soft pastel gradients.
