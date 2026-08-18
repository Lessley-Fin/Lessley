# frame.md — design truth for the Lessley demo

## The concept angle

**The product in its own light, held in the brand's dark hand.** The stage is deep navy —
the app's own `--gradient-navy`. The phone screen is the app's real light fintech theme,
untouched. That contrast is the whole design idea: the only bright thing on screen is the
product, so the eye never has to be told where to look.

Everything outside the phone is chrome and must stay quiet. Everything inside the phone is
the real app and must stay faithful.

---

## Two palettes, deliberately

### Stage (outside the phone) — dark

| Token                 | Value                   | Use                                                        |
| --------------------- | ----------------------- | ---------------------------------------------------------- |
| `--stage-bg`          | `oklch(19% 0.028 245)`  | Canvas ground. Deeper than the app's navy so the phone reads as the light source. |
| `--stage-surface`     | `oklch(24% 0.030 240)`  | Raised panels, chapter rail                                |
| `--stage-ink`         | `hsl(203 36% 96%)`      | Headlines, body — the app's own `--navy-foreground`        |
| `--stage-ink-muted`   | `hsl(203 13% 67%)`      | Sub-labels — the app's own `--navy-muted`                  |
| `--stage-accent`      | `hsl(180 45% 62%)`      | **The one accent.** Brand teal lifted for AA on navy.      |
| `--stage-accent-deep` | `hsl(182 38% 36%)`      | Glows and fills ONLY — the app's `--primary`. Never text on dark. |
| `--stage-gold`        | `hsl(33 86% 61%)`       | **Reserved.** Savings payoffs only — the ₪ figure, the discount pill. Nothing else. |

One accent hue (teal). Gold is a spend, not a color in the rotation — if it appears twice
in a scene, one of them is wrong.

### In-phone — the app's real tokens, verbatim

Copied from `lessley-frontend/src/index.css` `:root`. Do not adjust, re-tint, or "improve"
these. Fidelity is the deliverable.

```
--background: 203 34% 96%;   --foreground: 209 37% 15%;
--card: 0 0% 100%;           --primary: 182 38% 36%;
--muted: 198 28% 94%;        --muted-foreground: 208 11% 46%;
--accent: 179 50% 88%;       --accent-foreground: 182 73% 18%;
--success: 150 60% 45%;      --warning: 33 86% 61%;
--border: 201 21% 89%;       --navy: 208 34% 17%;
--radius: 1rem;
--gradient-navy: linear-gradient(150deg, oklch(31% 0.036 246), oklch(24% 0.03 240));
--gradient-teal: linear-gradient(135deg, oklch(58% 0.075 196), oklch(50% 0.065 205));
--shadow-card:  0 1px 2px oklch(30% 0.03 240 / 0.04), 0 8px 24px oklch(30% 0.03 240 / 0.06);
--shadow-float: 0 8px 32px oklch(25% 0.03 240 / 0.18);
```

The app shell's radial background (`.app-shell`) is part of the screen and must be
reproduced — the app is not flat white.

---

## Typography

Hebrew, RTL. None of the renderer's 18 pre-bundled families carry Hebrew glyphs, so both
faces are **self-embedded via `@font-face` from local woff2** in `assets/fonts/`. Do not
rely on an implicit Google fetch — it fails closed in cloud renders.

| Role                       | Face                             | Weights | Size (1920×1080)     |
| -------------------------- | -------------------------------- | ------- | -------------------- |
| Scene title (stage)        | **Frank Ruhl Libre** — Hebrew serif | 700     | 76px, -1% tracking   |
| Body / explainer (stage)   | **Heebo** — Hebrew sans          | 400/600 | 30px, 1.5 line-height |
| Label / chapter (stage)    | Heebo                            | 600     | 20px, +6% tracking   |
| ₪ payoff figure            | Heebo 800, `tabular-nums`        | 800     | 96px                 |
| **Inside the phone**       | Plus Jakarta Sans → Heebo fallback | 400–800 | app's real sizes, scaled with the device |

Serif title + sans body — a real pairing, and Frank Ruhl Libre is a genuine Hebrew serif
rather than a Latin face with bolted-on Hebrew.

All stage text is `direction: rtl; text-align: right`. Numbers and `₪` stay LTR-neutral
inside `<bdi>` so they never flip.

---

## Layout — the 16:9 stage

```
┌──────────────────────────────────────────────────────────┐
│                                         ┌ chapter 04/13 ┐│  ← edge anchor, top-right
│      ╭──────────╮                                        │
│      │          │        כותרת הסצנה                     │  ← title, right-aligned
│      │  iPhone  │        ─────────────                   │
│      │  430×932 │        שורת הסבר ראשונה                 │  ← body, RTL
│      │          │        שורת הסבר שנייה                  │
│      ╰──────────╯                                        │
│                            ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁              │  ← progress rail
└──────────────────────────────────────────────────────────┘
   phone: cx 620            text block: right edge at 1760
```

- **Focal:** the phone screen. Always the brightest thing in frame.

### Legibility — the rule that outranks fidelity

A whole phone screen on a 1920 canvas puts the app's real 15px body type at ~13px. The
sketch pass proved it unreadable. Two corrections, both mandatory:

1. **The in-phone UI renders at ~1.5× logical scale** — body 22px, labels 17px, headings
   28px, hero figures 56px+. Read it as a user with iOS "Larger Text" on. The consequence
   is fewer rows fit per screen, and that is correct: a scene shows the part of the screen
   its narration is about, not the whole scrollable page.
2. **Every scene declares one camera target.** The frame opens on the whole device, then
   pushes into the card the narration is discussing (`coordinate-target-zoom` /
   `viewport-change`) and holds there. The target is marked in the DOM with
   `data-camera-target` on exactly one element per scene.

This also pays a motion debt: a 15-second scene that would otherwise sit still now has a
mapped camera path — the "camera with intent" route, not idle wobble.

Fidelity to the real UI still governs *what* is on screen and *what it says*. Scale and
framing are cinematography, and cinematography wins when the two conflict.
- **Phone at rest:** `cx 620, cy 540`, scaled to 880px tall. Left of center — Hebrew reads
  right-to-left, so the text panel owns the right (where the eye starts) and the phone is
  what the eye travels *to*.
- **Hero moments** (the optimizer payoff, the close): the phone slides to true center
  (`cx 960`) via `nudge-curve` and the text panel clears. Reserved — at most 3 times.
- **Edge anchors:** chapter counter top-right; a hairline progress rail along the bottom
  that fills across the whole film (the only element that persists end to end besides the phone).
- **Safe margins:** 96px all sides.

## Background layer (4 decoratives, one shared motion)

1. Radial teal glow (`--stage-accent-deep` @ 14%) behind the phone — grounds it, sells the
   "phone is the light source" idea.
2. Hairline grid, 120px pitch, `--stage-ink` @ 3% — a ledger surface, thematically right
   for a finance product.
3. Ghost Hebrew wordmark "Lessley" at 4% opacity, very large, bottom-left bleed.
4. Fine grain overlay @ 3%.

Per motion doctrine, these do **not** idle-wobble. They react: the glow brightens on a
savings payoff, the grid parallaxes during a phone reposition. Motion performs or it
doesn't exist.

---

## The device frame

One reusable component (`compositions/components/device.html`) — iPhone 15 Pro proportions:
430×932 logical, 55px corner radius, titanium bezel (2px `hsl(210 8% 62%)` rim over a 10px
`oklch(28% 0.01 250)` body), Dynamic Island pill 126×37 at y=11, and a screen mask the app
screens render into.

**The device is the film's carrier.** It is built once and never rebuilt across a cut —
only its screen contents change. Every seam hands the phone across at matched position and
velocity. This is what stops 21 scenes from reading as 21 slides.

---

## Demo data — one user, one truth

Every scene shows the same fictional user. A figure that contradicts this table is a bug.
Copy values from here; never invent a new one mid-scene.

| Fact | Value |
| --- | --- |
| User | `dor.h` · `dor@example.com` · avatar initial `D` |
| Clubs joined (frame 5, everywhere after) | רמי לוי · שופרסל · סופר-פארם · Be — **4 clubs** |
| Match level | בינוני (50% עליונים) |
| Linked accounts | 3 |
| Optimizer cart (frames 10–12) | store רמי לוי · cart **₪412** · max 3 deals |
| Optimizer result | pay **₪317** · saved **₪95 (23%)** |
| Stack steps | ① coupon 15% → ₪350 · ② card ₪20 → ₪330 · ③ cashback 4% → ₪317 |
| Total saved (frames 1, 14, 21) | **₪1,284** across 4 clubs |
| Period shown | 30 ימים · 142 עסקאות · ₪5,630 |
| Top category | מכולת ₪2,140 (38%) |
| Top club match (frame 17) | מועדון חבר · 72% · 7/10 חנויות תואמות |
| Missed savings (frame 18) | ₪340 ברמי לוי · קטגוריית מכולת |
| Unread notifications | 3 |

`₪317` reads as ₪ then digits. Wrap every figure in `<span class="num">` (defined in
`_shared.html`) so the bidi algorithm cannot reorder it — the sketch pass showed `₪412`
rendering as `412₪` in running Hebrew text.

## Hard rules

- **RTL everywhere** — stage copy and in-phone UI both.
- **Every string inside the phone comes from `he.json`.** No invented UI copy. Ever.
- Demo figures are plausible and consistent across scenes (the same ₪412 cart, the same
  4 clubs) — one `demo-data.js` module, never re-typed per frame.
- No gradient text, no left-edge accent stripes, no neon. The app is a calm fintech
  product; the video is calm too.
- Contrast is a gate, not a preference — `hyperframes check` enforces AA.
