# Asset inventory — Lessley social promo

**No website capture was run.** This project's source is the Lessley repository itself
(`BRIEF.md` § Assets), so every asset below was staged by hand from
`videos/lessley-demo/assets/`, which already holds the brand-approved set. No asset was
downloaded, scraped, or generated.

## Brand marks

| File | What it is | Where it belongs |
| --- | --- | --- |
| `capture/assets/logo-without-name.svg` | Lessley robot mascot, mark only. 2000×2000 viewBox, flat paths, no text. Reads as a headset-wearing robot holding a magnifier, with a green ↗ arrow and a `$` glyph. | Opening beat and the closing lockup. Also the in-phone header mark. |
| `capture/assets/logo-with-name.svg` | Same mark plus the `Lessley` wordmark, horizontal lockup. | The closing CTA card only. |

## Loyalty-club logos — the ten real clubs

These are the actual club marks from the `lessley.clubs` collection. They carry the whole
"open banking → ten clubs" beat and the closing collapse-into-one-card move. All are
raster; sizes are small, so use them at chip scale (≤ 220px wide) and never blown up
full-frame.

| File | Club | Notes |
| --- | --- | --- |
| `capture/assets/mastercard_logo.jpg` | Mastercard Israel | The top club match (29% · 10/35 stores). Needs the most screen time of the ten. |
| `capture/assets/topcash_logo.png` | Isracard TopCash | Runner-up match (10% · 31/300). PNG, transparent. |
| `capture/assets/hever_giftcard_logo.jpg` | Hever (חבר) — Gift Cards | **The winning deal's club.** Carries the ₪1,000 → ₪700 beat. |
| `capture/assets/hever_teamim_logo.jpg` | Hever (חבר) — טעמים | Chip field only. |
| `capture/assets/hvr_logo.png` | Hever house mark | Alternate Hever mark; use only if the two Hever chips need visual separation. |
| `capture/assets/paisplus_logo.jpg` | PaisPlus | Chip field. |
| `capture/assets/paisplus_logo2.jpg` | PaisPlus, alternate lockup | Fallback if `paisplus_logo.jpg` reads poorly at chip scale. |
| `capture/assets/paisplus_food_chains_logo.png` | PaisPlus — Food Chains Cash Card | Chip field. Also one of the two deals the engine legally rejects. |
| `capture/assets/paisplus_networks_logo.jpg` | PaisPlus — Networks Cash Card | Chip field. The second legally-rejected deal. |
| `capture/assets/hot_logo.png` | HOT Israel | Chip field. PNG, transparent. |
| `capture/assets/swish_logo.png` | Swish (נפשונית) | Chip field. PNG, transparent. |
| `capture/assets/swish_logo2.jpg` | Swish, alternate | Fallback only. |

**Behatsdaa (בהצדעה)** is the tenth club and has **no logo file**. Render it as a
type-only chip in the same chip shape so the field still reads as ten.

## Fonts — self-embedded, not fetched

`capture/assets/fonts/` carries both faces as woff2 with a ready `fonts.css`. None of the
renderer's pre-bundled families carry Hebrew glyphs, and a Google Fonts fetch fails closed
in a cloud render, so these must be `@font-face`'d from local files.

| Family | Weights on disk | Role |
| --- | --- | --- |
| **Heebo** | 400, 600, 800 (Hebrew + Latin subsets) | Body, labels, all ₪ figures (`tabular-nums` at 800). |
| **Frank Ruhl Libre** | 700 (Hebrew + Latin) | Display headlines. A genuine Hebrew serif, not a Latin face with bolted-on Hebrew. |

## Screen material — rebuilt, not screenshotted

There are no app screenshots in this inventory and none are needed. The demo project at
`videos/lessley-demo/compositions/frames/` already holds every Lessley screen rebuilt as
faithful HTML against the real design tokens. Those are the source for this video's
in-phone glimpses — copy the component markup, not the whole frame. The brief calls for
free motion graphics with glimpses of the screen, so only these screens are needed:

- `10-optimizer-input.html` / `11-optimizer-stack.html` / `12-optimizer-steps.html` — the optimizer beat.
- `07-signup-banking.html` — the open-banking connect screen.
- `05-signup-clubs.html` — the ten-club grid.
- The remaining capability screens appear as **detached cards only** (a single stat card,
  a single deal card, one club-match row), never as a full screen.

## Icons

The real app leans on emoji for category dots and card glyphs. Headless Chrome has **no
emoji font**, so every icon in this video must be authored as inline SVG. There is no
icon asset file to stage — this is a build constraint, recorded here so the frame workers
inherit it.
