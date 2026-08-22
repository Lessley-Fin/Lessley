---
version: alpha
name: Blue Professional — Frame (video / frame layer)
description: >
  Video-first companion to Blue Professional's design.md. The unit is the frame (1920×1080). Atoms
  are identical and sacred — the warm cream canvas, a single brand teal (#397c7f) as the only
  accent, the three-step gray text ladder, Frank Ruhl Libre 700 (Hebrew serif display) + Heebo 400/600/800 (body, chrome, numerals),
  soft teal-tinted cards (4% fill / 20% border / 10–14px radius) with NO shadows, pill chrome, and
  the teal progress bar. Composition + frame scale rewritten. Motion out of scope.
unit: the frame — 1920×1080 primary; 9:16 and 1:1 documented
principle: atoms are sacred · composition is free · numbers come from the script

colors:
  bg: "#f1f6f8"
  primary: "#397c7f"
  text: "#182734"
  text-muted: "#687682"
  text-light: "#9A9A9A"
  accent-light: "rgba(57, 124, 127, 0.08)"
  accent-medium: "rgba(57, 124, 127, 0.15)"
  border: "rgba(57, 124, 127, 0.2)"
  card-bg: "rgba(57, 124, 127, 0.04)"
  positive: "#059669"
  negative: "#dc2626"
  # RATIONED — the app's --warning. ₪ payoff figures and the discount pill ONLY.
  # If it appears twice in one frame, one of them is wrong.
  payoff: "#f1a446"
  # The dark ground for inverted frames (the app's --navy).
  ground-dark: "#1d2c3a"
  ground-dark-ink: "#f1f6f8"
  ground-dark-muted: "#a0adb6"

radii:
  pill: "100px"
  card-lg: "14px"
  card-md: "12px"
  card-sm: "10px"
  bar: "6px"
  circle: "50%"

typography:
  # — reading ramp (Heebo body + Heebo chrome) —
  body:    { fontFamily: "Heebo", cqw: 0.85, weight: 400, lineHeight: 1.6, color: "text-muted" }
  h4-eyebrow:{ fontFamily: "Heebo", cqw: 0.8, weight: 600, tracking: "0.08em", upper: true, color: "primary" }
  tag:     { fontFamily: "Heebo", px: 12, weight: 600, color: "primary" }
  counter: { fontFamily: "Heebo", px: 13, weight: 600, tracking: "0.05em", color: "text-muted" }
  # — display ramp (Frank Ruhl Libre 700 headings) · numerals stay Heebo 800 tabular —
  h3:      { fontFamily: "Frank Ruhl Libre", cqw: 1.25, weight: 700, lineHeight: 1.3, tracking: "-0.02em", color: "text" }
  stat-num:{ fontFamily: "Heebo", cqw: 1.9, weight: 800, lineHeight: 1.0, color: "primary" , numeric: "tabular-nums" }
  blockquote:{ fontFamily: "Frank Ruhl Libre", cqw: 2.4, weight: 700, lineHeight: 1.35, color: "text" }
  h2:      { fontFamily: "Frank Ruhl Libre", cqw: 2.6, weight: 700, lineHeight: 1.1, tracking: "-0.02em", color: "text" }
  metric-value:{ fontFamily: "Heebo", cqw: 3.0, weight: 800, lineHeight: 1.0, color: "primary" , numeric: "tabular-nums" }
  h1:      { fontFamily: "Frank Ruhl Libre", cqw: 4.2, weight: 700, lineHeight: 1.08, tracking: "-0.02em", color: "text" }
  quote-mark:{ fontFamily: "Frank Ruhl Libre", cqw: 8.0, weight: 700, lineHeight: 0.5, color: "primary", opacity: 0.15 }

spacing:
  pad-x: "5cqw"
  pad-y-top: "5cqw"
  gap-cards: "1.4cqw"
  accent-line: "60px × 4px"

components:
  card-tinted:
    backgroundColor: "{colors.card-bg}"
    border: "1.5px solid {colors.border}"
    rounded: "{radii.card-lg}"
    shadow: "none"
    description: "Universal content card. Never solid-colored, never opaque-bordered, NO shadow."
  metric-card:
    backgroundColor: "{colors.card-bg}"
    border: "1.5px solid {colors.border}"
    rounded: "{radii.card-lg}"
    typography: "{typography.metric-value} ({colors.primary}) + {typography.metric-label} + {typography.metric-desc}"
    description: "+ optional inline ↑/↓ change chip ({colors.positive}/{colors.negative} text, no fill)."
  tag-pill:
    backgroundColor: "{colors.accent-light}"
    textColor: "{colors.primary}"
    rounded: "{radii.pill}"
    typography: "{typography.tag}"
    description: "Top-right of the slide-header."
  cta-button:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.bg}"
    rounded: "{radii.pill}"
    typography: "Heebo 600"
    shadow: "soft cobalt on hover only — the system's only shadow"
    description: "The one solid element."
  accent-line:
    backgroundColor: "{colors.primary}"
    size: "60×4, 2px radius"
    description: "Above cover titles / eyebrow separators."
  bar-track:
    backgroundColor: "{colors.accent-light}"
    fill: "{colors.primary} (display:block so width resolves)"
    rounded: "{radii.bar}"
    description: "28px track; fill carries the value."
  step-circle:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.bg}"
    rounded: "50%"
    size: "56px"
    description: "Sequential steps fade opacity 1.0→0.85→0.7→0.55."
  split-highlight:
    backgroundColor: "{colors.accent-light}"
    borderLeft: "4px solid {colors.primary}"
    rounded: "{radii.card-md}"
    description: "Inline pull-quote callout."
  slide-header:
    typography: "{typography.h4-eyebrow} (cobalt) left, tag-pill right; {typography.h2} below"
    description: "Top band of every content frame."
  atmosphere:
    elements: "clipped diagonal cobalt-tint panel, 3×3 cobalt dot grid, concentric closing rings"
    description: "Cover/closing only. Never on content frames."
  progress-bar:
    backgroundColor: "{colors.primary}"
    size: "3px tall, bottom edge, width grows with index"
    description: "Persistent progress strip."
---

# Blue Professional — Frame (video / frame layer)

## Brand adaptation (READ FIRST — the frontmatter is the source of truth)

This is the **blue-professional** preset remixed onto the captured brand. The YAML frontmatter above (colors · typography · components) is **normative and already correct — use it verbatim.** The prose below is the ORIGINAL preset's intent; read it THROUGH the frontmatter:

- **Fonts** — already set to **Frank Ruhl Libre** (display) / **Heebo** (body); ignore any preset font name lingering in prose.
- **Colors** — use the frontmatter hex; preset color NAMES in prose (e.g. "cobalt", "cream") mean the remapped brand values.


## Overview

Blue Professional at frame scale is a **consulting-grade system: restraint with one strong
commitment.** A warm cream canvas and a single saturated cobalt that carries every accent —
eyebrow, metric, CTA, chart fill, progress bar. No secondary brand color, no pastels, just cream,
cobalt, and a tight ladder of grays. The register is investment-research / McKinsey briefing:
measured, data-dense without crowding, executive-readable at distance.

The voice is two faces in fixed roles: **Frank Ruhl Libre** (display, every numeral, all chrome —
eyebrows uppercase 0.08em) and **Frank Ruhl Libre** (body, muted gray, line 1.6). Headlines are near-black;
cobalt is reserved for accent moments. Depth is **soft and tinted** — 4% cobalt card fills with 20%
cobalt borders and 10–14px radii — never shadowed. The lack of harsh shadows is the premium signal.

**Key characteristics at frame scale:**

- **Warm cream ground** on every frame; **single cobalt** as the only accent.
- **Frank Ruhl Libre** (display/numerals/chrome) + **Frank Ruhl Libre** (body) — near-black headlines, cobalt numerals.
- **Tinted cards** — cobalt 4% fill, cobalt 20% 1.5px border, 10–14px radius, **no shadow**.
- **Pill chrome** (100px) — tag pills + the one solid cobalt CTA; cobalt **progress bar**.
- **Soft rounded corners everywhere** (no square corners save the progress bar).
- **Atmosphere** (diagonal panel, dot grid, concentric rings) on cover/closing only.

## The Frame

### Frame Craft Bar

Three eyeball tests gate every frame before any structural check:

- **Squint** — one **near-black headline or cobalt numeral** dominates at 3–6× its neighbor.
- **Silence** — content frames read **balanced, not crowded**; the **dashboard is the one dense exception**.
- **Restraint** — a **single cobalt accent** carries everything; headlines stay near-black (never cobalt); no shadows (tinted cards do the lift); positive/negative inline-text only.
- **Reference** — aim at an **investment-research / McKinsey quarterly briefing**; failure looks like a **heavy-outlined, multi-color dashboard**.

- **Primary:** 1920×1080 (16:9). Display authored in **`cqw`** (`px ÷ 1920 × 100 = cqw`).
- **Vertical:** 1080×1920 (9:16). **Square:** 1080×1080 (1:1).
- **Safe area:** `pad-x` 5cqw; bottom reserves room for the counter + progress bar.

**The container law (load-bearing).** Every frame ground sets `container-type: size`; ALL
frame-relative units are `cqw`/`cqh` against it — never `vw`. Card radii stay px (10–14px); the
pill radius stays 100px; borders stay 1–1.5px.

## Colors

Tokens identical to the source. `{colors.bg}` cream is the universal ground; `{colors.primary}`
cobalt is the **only** accent — every eyebrow, numeral, CTA, chart fill, progress bar, and the 4px
highlight left-rule. Headlines are `{colors.text}` near-black (never cobalt); body is
`{colors.text-muted}`; tertiary is `{colors.text-light}`. Cards fill `{colors.card-bg}` (4%) with
`{colors.border}` (20%) borders. `{colors.positive}`/`{colors.negative}` appear **only inline** on
directional change chips — never as fills. **No second accent color.**

## Typography

Two ramps. The **reading ramp** (Frank Ruhl Libre body 0.85cqw muted; Frank Ruhl Libre eyebrow uppercase 0.08em
cobalt) carries copy + chrome; the **display/numerical ramp** (Frank Ruhl Libre `h3` 1.25cqw → `h1`
4.2cqw near-black; numerals `stat-num`/`metric-value` in cobalt) carries headings and figures.

- **Legibility floor:** any load-bearing line ≥ **1.4cqw**; px chrome (tag/counter) is colophon only.
- **Fit-to-measure:** size the headline to its length. Cap the block at **≤ 78cqw**; ≤3 words → `h1`; 4–6 → `h2`; 7+ → `h3`. Cobalt numerals scale `metric-value`→`stat-num` by card size.
- **Headlines near-black, −0.02em**; **eyebrows cobalt, uppercase, 0.08em**; **numerals cobalt 600–700**; **body Frank Ruhl Libre 400 muted, line 1.6**. No italic, no uppercase body, no cobalt headline.

## Depth & Surface

Soft and tinted — never offset. Depth from:

- **Tinted cards** — 4% cobalt fill + 20% cobalt 1.5px border + 10–14px radius reads as lifted without offset.
- **Border-left accent** — the 4px cobalt rule on split-highlight blocks pulls a callout forward.
- **Rounded corners** — the 10–14px radius is part of the softness; square corners break it.

**Ceiling:** zero box-shadow on content (the only shadow is a soft cobalt CTA _hover_); no opaque cobalt borders; no harsh outlines.

## Shapes

- **100px** — tag pills, CTA, nav buttons (pill chrome).
- **14/12/10px** — cards by size (large metric / standard stat / detail + mini).
- **6px** — bar tracks + fills. **50%** — step circles, nav circles, dots, closing rings.
- **0** — only the progress bar. No square-cornered content.

## Components

- **card-tinted / metric-card** — the universal soft-tint content cards (no shadow).
- **tag-pill / cta-button / accent-line** — the cobalt pill chrome + the one solid CTA + the 60×4 rule.
- **bar-track / step-circle / split-highlight** — cobalt data + sequence + callout patterns.
- **slide-header** (eyebrow + tag pill) — the structural rhythm; **atmosphere** (diagonal/dots/rings) on cover/closing only; **progress-bar** on every frame.

## Frame Treatments

> Recipe: ground · container · composes · focal · chrome · accent · silence · Fixed/Free · density.
> Atmosphere only on cover/closing; content frames carry the slide-header rhythm.

### 1 · Cover (identity · move: diagonal accent · left)

**Ground** cream + the clipped diagonal cobalt-tint panel (right ~36%) + a 3×3 cobalt dot grid.
**Composes** accent-line, meta, h1, body sub. **Focal** a 2-line Frank Ruhl Libre `h1` near-black, left,
under a cobalt accent-line + meta. **Chrome** counter + progress bar. **Accent** the cobalt line +
diagonal panel. **Silence** the diagonal panel holds the right third. **Fixed** near-black h1, cobalt
accents, atmosphere here only. **Free** title, meta. **Density** low.

### 2 · Dashboard (data · move: 3-up metric grid · the dense frame)

**Ground** cream, `pad-x`. **Composes** slide-header (eyebrow + tag-pill), h2, 3× metric/tinted card.
**Focal** a row of tinted cards — cobalt `metric-value` + Frank Ruhl Libre label + muted desc + optional
green/red change chip. **Chrome** eyebrow left, tag-pill right; progress bar. **Accent** the cobalt
numerals. **Silence** tight — the density exception. **Fixed** 4% tint cards, 20% borders, no shadow,
cobalt numerals. **Free** figures (from script), labels. **Density** dense-exception.

### 3 · Bar Ranking (data · move: teal bars · left)

**Ground** cream, `pad-x`. **Composes** eyebrow, h2, bar-track rows. **Focal** 3–5 labeled
cobalt-fill bars on cobalt-8% tracks with cobalt percentages. **Chrome** eyebrow; progress bar.
**Accent** the cobalt fills + figures. **Silence** moderate. **Fixed** 6px tracks, cobalt fills.
**Free** rows, values (from script). **Density** standard.

### 4 · Pull Quote (quote · move: concentric rings · centered)

**Ground** cream, centered, with faint concentric closing-rings behind. **Composes** quote-mark,
blockquote, cite. **Focal** a Frank Ruhl Libre `blockquote` near-black under a 15%-opacity cobalt
quote-mark; an uppercase cobalt-muted cite beneath. **Accent** the faint rings + quote-mark. **Silence**
~55%. **Fixed** near-black quote, soft rings. **Free** quote, cite. **Density** low.

### 5 · Split + Highlight (content · move: asymmetric split · left)

**Ground** cream, two columns. **Composes** eyebrow, h2, body, split-highlight block. **Focal** an
Frank Ruhl Libre body column beside a cobalt-8% highlight block (4px cobalt left rule) carrying an inline pull
quote. **Accent** the highlight's left rule. **Silence** generous gutter. **Fixed** tinted highlight,
4px cobalt rule. **Free** body, callout. **Density** standard.

### 6 · Closing / CTA (closer · move: centered rings + CTA)

**Ground** cream + concentric closing-rings. **Composes** accent-line, h1, body, cta-button. **Focal**
a Frank Ruhl Libre `h1` near-black, centered, with the one solid cobalt `cta-button` pill below. **Accent**
the CTA + rings. **Silence** ~60%. **Fixed** one CTA, near-black h1, soft rings. **Free** sign-off, CTA
label. **Density** low.

## Composition Rules

### Do

- Start every frame on **warm cream**; let **cobalt carry every accent** (eyebrow, numeral, CTA, bar, progress).
- Set headlines **near-black, −0.02em**; eyebrows **cobalt uppercase 0.08em**; numerals **cobalt 600–700**.
- Use **tinted cards** (4% fill, 20% border, 10–14px radius, no shadow); body Frank Ruhl Libre 400 muted, line 1.6.
- Keep all chrome **pill-shaped (100px)**; one solid cobalt CTA per closing frame.
- Reserve **atmosphere** (diagonal panel, dots, rings) for cover/closing; content frames keep the slide-header rhythm.
- Lean left on cover/dashboard/split, centered on quote/closer.

### Don't

- No second accent color; no cobalt headlines.
- No drop shadows on content (only the soft cobalt CTA hover); no opaque cobalt borders.
- No square corners (save the progress bar); no font substitutes; no uppercase body.
- Don't use the green/red change chips as general accents — directional comparisons only.
- Don't fill space with heavier borders — add substance; don't blow a headline edge-to-edge.

## Aspect-Ratio Behavior

| Treatment         | 16:9                       | 9:16                           | 1:1                      |
| ----------------- | -------------------------- | ------------------------------ | ------------------------ |
| Cover             | title left, diagonal right | title top, diagonal band below | title upper, dots corner |
| Dashboard         | 3 cards across             | 3 stacked                      | 2×2                      |
| Bar Ranking       | 3–5 bars                   | 3–5 bars (tighter)             | 3 bars                   |
| Pull Quote        | centered, rings behind     | centered, taller               | centered                 |
| Split + Highlight | side-by-side               | stacked                        | stacked                  |
| Closing / CTA     | centered + CTA             | centered + CTA                 | centered + CTA           |

`pad-x` holds on the short edge; re-step display above the 1.4cqw floor. The diagonal cover panel
becomes a top/bottom band on 9:16. Numerals stay Latin Arabic digits in CJK builds.

## Approved Entities

**Ten real loyalty clubs are approved and staged** — Mastercard Israel, Isracard TopCash,
Hever Gift Cards, Hever טעמים, PaisPlus (×3), HOT Israel, Behatsdaa, Swish. Their marks live in
`capture/assets/logos/` (Behatsdaa is type-only — no logo file exists). One real store is
approved: **FOX - פוקס**. Nothing else. Never invent a club, store, or partner mark.

## Numerals & Claims (hard rule)

Never invent figures, financials, percentages, or dates at frame scale. Render slots as `— figure —`,
`{metric}`, `+NN%`, `↑ —`. Metric cards, bar values, and stat cells especially carry placeholders
until the script supplies them. Directional chips require a real comparison from the script.

## Pre-Render Self-Audit

- **Squint** — one near-black headline or teal numeral dominates per frame.
- **Silence** — content frames balanced, not crowded; only the dashboard runs dense.
- **Single accent** — teal only; headlines near-black; positive/negative inline only.
- **Type** — Frank Ruhl Libre headings −0.02em near-black, teal eyebrows 0.08em + Heebo 800 numerals; Heebo body muted line 1.6; ≥1.4cqw floor.
- **Depth** — tinted cards (no shadow), soft rounded corners, 20% teal borders; no square content corners.
- **Anchor** — left on cover/dashboard/split, centered on quote/closer; atmosphere on cover/closing only.
- **Fabrication** — every numeral traces to the script, else placeholder.

## Known Gaps

- **Motion intentionally out of scope.** frame.md specifies composition only; the source's 500ms translateX transitions + bar-fill animations are deck mechanics.
- **Fonts are self-embedded, not fetched.** Frank Ruhl Libre 700 + Heebo 400/600/800 load from `assets/fonts/` via the `@font-face` block below. A Google Fonts fetch fails closed in a cloud render, so never reintroduce one. The CJK pairing in the source preset does not apply — this video is Hebrew only.
- **9:16 / 1:1 are guidance**; verify the floor and that the diagonal panel reflows to a band.
- Diagonal panel (clip-path), dot grid, concentric rings, and bars are CSS-only; no external imagery is required.


## Font loading (auto-generated)

The brand font ships as local files in `assets/fonts/` — do NOT link Google Fonts for it. Paste this `<style>` into every frame's `<head>`/`<template>` (captions use the same files) so `font-family` resolves in preview, snapshot, and render alike:

```html
<style>
@font-face{font-family:"Heebo";font-weight:400;font-style:normal;font-display:block;src:url("assets/fonts/heebo-400-hebrew.woff2") format("woff2");unicode-range:U+0307-0308, U+0590-05FF, U+200C-2010, U+20AA, U+25CC, U+FB1D-FB4F;}
@font-face{font-family:"Heebo";font-weight:400;font-style:normal;font-display:block;src:url("assets/fonts/heebo-400-latin.woff2") format("woff2");unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215;}
@font-face{font-family:"Heebo";font-weight:600;font-style:normal;font-display:block;src:url("assets/fonts/heebo-600-hebrew.woff2") format("woff2");unicode-range:U+0307-0308, U+0590-05FF, U+200C-2010, U+20AA, U+25CC, U+FB1D-FB4F;}
@font-face{font-family:"Heebo";font-weight:600;font-style:normal;font-display:block;src:url("assets/fonts/heebo-600-latin.woff2") format("woff2");unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215;}
@font-face{font-family:"Heebo";font-weight:800;font-style:normal;font-display:block;src:url("assets/fonts/heebo-800-hebrew.woff2") format("woff2");unicode-range:U+0307-0308, U+0590-05FF, U+200C-2010, U+20AA, U+25CC, U+FB1D-FB4F;}
@font-face{font-family:"Heebo";font-weight:800;font-style:normal;font-display:block;src:url("assets/fonts/heebo-800-latin.woff2") format("woff2");unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215;}
@font-face{font-family:"Frank Ruhl Libre";font-weight:700;font-style:normal;font-display:block;src:url("assets/fonts/frank-ruhl-libre-700-hebrew.woff2") format("woff2");unicode-range:U+0307-0308, U+0590-05FF, U+200C-2010, U+20AA, U+25CC, U+FB1D-FB4F;}
@font-face{font-family:"Frank Ruhl Libre";font-weight:700;font-style:normal;font-display:block;src:url("assets/fonts/frank-ruhl-libre-700-latin.woff2") format("woff2");unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215;}
</style>
```

---

## Lessley overrides (this video — read after everything above)

The preset supplied brand and composition. These six rules are what this specific video
adds, and they **outrank** the preset wherever they disagree.

### 1 · Vertical is the unit, not 1920×1080

The canvas is **1080×1920**. Every "left-anchored" instruction in the preset above assumed
a landscape frame with room beside the subject; vertical has no beside. Translate it:

- Text sits **above or below** the subject, never beside it.
- Safe margins: `120px` top, `220px` bottom (feed chrome eats the bottom), `72px` sides.
- The eye enters at the vertical middle. Put the payoff there, not at the optical center
  of the full canvas.

### 2 · RTL is structural, not a text-align

Hebrew reads right-to-left, so **every directional gesture reverses**:

- Staggered word reveals fire right → left.
- Progress rails, bar fills, and the marker swipe all grow from the **right** edge.
- Card cascades enter from the right.
- `dir="rtl"` goes on a container element. **Never on `<html>`** — it renders the whole
  video black. This is a confirmed failure from the sibling demo project.
- Wrap every figure in a `<span class="num">` (isolation: isolate) so the bidi algorithm
  cannot reorder `₪700` into `700₪`.

### 3 · Two grounds, one wipe

Only two grounds exist: `bg` (#f1f6f8) and `ground-dark` (#1d2c3a). There is no third.
They swap via a **giant soft-edged circle mask** that sweeps the frame — this is the film's
signature transition and the only ground change permitted. On a dark ground, ink becomes
`ground-dark-ink` and muted becomes `ground-dark-muted`.

A frame's ground is its own full-duration `class="clip"` background layer, never a
`background` on `#root`.

### 4 · The marker swipe

The single most important text device, because this video has **no voiceover** — the text
is the narrator. A headline lands in `text-muted`; its payoff word then takes a
`primary`-tinted marker swipe that grows from the right, and the word flips to `text`.
One swipe per frame. A second swipe in the same frame means the frame has two payoffs,
which means it has none.

### 5 · Cards detach from the device

The explainer engine. UI does not stay trapped behind glass: a card lifts out of the phone,
scales up ~1.8×, and stands alone in the open field where it is actually readable at
vertical scale; then it returns, or is replaced. Detached cards are real app components
copied from `videos/lessley-demo/compositions/frames/`, not redrawn approximations.

The device itself is a **carrier** — built once, handed across cuts at matched position and
scale. It never resizes between scenes.

### 6 · Gold is a spend

`payoff` (#f1a446) is reserved for the ₪ figure at a savings moment and the discount pill.
Nothing else, ever. Teal is the accent; gold is an event.

### Icons

Headless Chrome has **no emoji font** and Heebo carries no arrows or symbols. Every icon,
arrow, check, and glyph is **inline SVG**. An emoji character in the DOM renders as an
empty box.
