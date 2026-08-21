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
│                                         ┌ chapter 04/21 ┐│  ← edge anchor, top-right
│      ╭──────────╮                                        │
│      │          │        כותרת הסצנה                     │  ← title, right-aligned
│      │  iPhone  │        ─────────────                   │
│      │  460×997 │        שורת הסבר ראשונה                 │  ← body, RTL
│      │          │        שורת הסבר שנייה                  │
│      ╰──────────╯                                        │
│                            ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁              │  ← progress rail
└──────────────────────────────────────────────────────────┘
   phone: cx 620            text block: right edge at 1760
```

- **Focal:** the phone screen. Always the brightest thing in frame.

### Fidelity outranks everything — revised 18/08 against real app screenshots

**No in-phone camera. No zoom. Ever.** The earlier "push into the card" rule is withdrawn
by the client. `.screen-world` holds `scale(1)`, `x: 0`, `y: 0` for the entire film. Any
`data-camera-target` attribute still in the DOM is inert and must not be animated.

**The screen must be indistinguishable from a screen recording of the real app** — not an
interpretation, not a tidier version. Where this spec and design instinct disagree, the
spec wins.

Legibility is bought with **frame real estate, not magnification**: the device is held
large in frame and the UI renders at its real proportions.

### The real UI — component spec

Reproduce exactly. Every value below is read off the running app.

**Header** (every authenticated screen) — white bar, hairline bottom border. RTL order:
robot mascot logo (~46px: headset, magnifier, green ↗, `$`) · `Lessley` 23px/800 with
`טייס אוטומטי פיננסי` 15px muted beneath · then a bell in a white circle button (border +
shadow) · then the avatar circle in `--accent` mint carrying the initial in
`--accent-foreground`. Bell and avatar sit at the **left** edge.

**Bottom nav** — `--gradient-navy` rounded-full bar inset from the screen edges, ~78px tall.
Four items, icon over a 13px label: אופטימיזציה (sparkles) · תובנות (bar chart) · חם (flame) ·
המלצות (lightbulb). The active item is a **filled teal rounded-full pill** with dark-teal
ink; inactive labels are `--navy-muted`.

**Page head** — right-aligned title 34px/800, subtitle 18px `--muted-foreground`.

**Period selector** — white rounded-full track, four options; the active one is a **filled
dark-navy pill with white text**. Navy, not teal — teal means action.

**Savings hero** — dark navy rounded-3xl card. Top-right `נחסך עם LESSLEY` in small
letterspaced caps (`--navy-muted`); top-left a `?` circle button; the figure at ~58px/800 in
white; beneath it `90 הימים האחרונים · 10 מועדונים` at 15px muted.

**Stat cards** — white rounded-2xl pairs. Icon + label top-right, figure 30px/800, caption
14px muted.

**Deal card** — white rounded-3xl. Discount pill (`20% הנחה`) **top-left**, teal-filled,
white text. Rank badge top-right: white circle, hairline border, numeral. A large product
emoji centred. Then right-aligned: store name 20px/700 · category 15px muted · deal title
20px/700 · a row carrying a date chip (calendar glyph + `08/08/2026`) and a club chip.

**Optimizer tabs** — white rounded-full track; the active tab is **teal-filled, white text**.

**Winning stack** — a **teal band** across the card top (rounded top corners) carrying a
trophy in a translucent circle plus `השילוב הטוב ביותר` and `מגה ספורט · 3 דילים הופעלו`.
White body beneath: `אתם משלמים` label, the figure at ~52px/800 in `--primary`, then a row
with the savings pill (mint fill, teal ink) beside the original price struck through.

**Stack step** — mint-tinted rounded-2xl. Teal numeral circle on the right, store name,
`כרטיס מתנה` chip, provider slug beneath. Discount pill on the left (mint fill, teal ink)
with `−₪300.00` under it. Then three label/value rows — `ההנחה חלה על` / `משלמים עליו` /
`נשאר לתשלום` — the last carrying the struck previous balance. Footer: two pill buttons,
`פרטים` and `מעבר לדיל`. A chevron sits between consecutive steps.

**Club match row** — mint rounded-2xl. Rank circle right, club name + card glyph, then
`10/35 חנויות תואמות` muted beneath. A `%` badge on the left in a mint pill. A progress
track runs along the bottom: white track, teal fill, **filling from the right**.

**Settings** — a profile card (avatar + name + email), then a white card of rows; each row
carries a mint circular icon on the right, a 20px/700 title with muted subtitle, and a
chevron at the far left.

**Preference chips** — rounded-full. Selected: mint fill + teal border. Unselected: white
with a hairline border.

**Primary button** — teal filled, rounded-full, white 22px/700, full width.

**Emoji.** The real app leans on emoji — product images, category dots, card glyphs.
Headless Chrome has **no emoji font**, so each one ships as inline SVG. That is a rendering
constraint, not licence to redesign.
- **Phone at rest:** `cx 620, cy 540`, at its **natural 460×997 — no scale transform.**
  Since the in-phone camera was removed, frame real estate is the only legibility lever the
  film has left, so the device is never shrunk. `scale(0.88…)` in any scene is a leftover
  from the 430×932 device and must be deleted: the carrier may not change size between
  scenes, and a viewer reads a resized phone as a mistake.
  Left of center — Hebrew reads right-to-left, so the text panel owns the right (where the
  eye starts) and the phone is what the eye travels *to*.
- **Hero moments** (the optimizer payoff, the close): the phone slides to true center
  (`cx 960`) via `nudge-curve` and the text panel clears. Reserved — at most 3 times.
  This is a translation only; it never rescales the device.
- **Edge anchors:** chapter counter top-right; a hairline progress rail along the bottom
  that fills across the whole film (the only element that persists end to end besides the phone).
- **Safe margins:** stage padding `42px 80px`. The device is 997px tall inside a 1080 canvas,
  so vertical margin is deliberately tight — that is the trade that bought back legibility.

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

The device chrome lives in `_shared.html` as `.device` / `.device-body` / `.device-screen`.
iPhone 15 Pro proportions at 460×997, 62px corner radius, titanium bezel (2px `hsl(210 8% 62%)` rim over a 10px
`oklch(28% 0.01 250)` body), Dynamic Island pill 126×37 at y=11, and a screen mask the app
screens render into.

**The device is the film's carrier.** It is built once and never rebuilt across a cut —
only its screen contents change. Every seam hands the phone across at matched position and
velocity. This is what stops 21 scenes from reading as 21 slides.

---

## Demo data — one user, one truth

Every scene shows the same fictional user. A figure that contradicts this table is a bug.
Copy values from here; never invent a new one mid-scene.

**Every club and store name below is real** — read from the `lessley.clubs` and
`lessley.deals` collections, not invented. Do not substitute plausible-sounding names.

**The ten supported clubs** (the complete `clubs` collection — frame 5 shows all ten):

`Mastercard Israel` · `Isracard TopCash` · `Hever (חבר) — Gift Cards` ·
`Hever (חבר) — טעמים` · `PaisPlus` · `PaisPlus — Food Chains Cash Card` ·
`PaisPlus — Networks Cash Card` · `HOT Israel` · `Behatsdaa` · `Swish (נפשונית)`

| Fact | Value |
| --- | --- |
| User | `dor.h` · `dor@example.com` · avatar initial `D` |
| Clubs selected in frame 5 | Mastercard Israel · Isracard TopCash · Hever (חבר) — Gift Cards · PaisPlus — **4 of the 10** |
| Match level | בינוני (50% עליונים) |
| Linked accounts | 3 |
| Optimizer cart (frames 10–12) | store **FOX - פוקס** · cart **₪1,000** · max 3 deals |
| Optimizer result | pay **₪700** · saved **₪300 (30%)** |
| The winning deal | `Hever (חבר) — Gift Cards` · כרטיס מתנה · 30% הנחה, capped at ₪300 · `hever_gift_card_company` |
| Stack step row | ההנחה חלה על `₪1,000` · משלמים עליו `₪700` · נשאר לתשלום `₪700` (was `₪1,000`) |
| Total saved (frames 1, 14, 21) | **₪1,284** across 10 clubs |
| Period shown | 30 ימים · 142 עסקאות · ₪5,630 |
| Top category | ביגוד ואביזרים ₪2,140 (38%) |
| Top club match (frame 17) | Mastercard Israel · 29% · 10/35 חנויות תואמות · runner-up Isracard TopCash · 10% · 31/300 |
| Missed savings (frame 18) | ₪340 ב-FOX - פוקס · קטגוריית ביגוד ואביזרים |
| Unread notifications | 3 |

**Why FOX ₪1,000 → ₪700 is the right example:** it is a real, verifiable deal. The Hever
gift-card deal on FOX is `percentage_off 0.3` with `max_discount_amount: 300`, so a ₪1,000
cart is exactly the cart where the cap bites and the headline 30% is genuinely delivered.
The two PaisPlus FOX deals cannot join it — they are also `giftcard_discount`, one carries
`stackable_with_giftcards: false`, and they share `exclusive_group: paisplus:chit-5001`.
So the engine correctly returns a **one-deal** stack, and the film should say so rather
than inventing a three-deal stack that the real engine would reject.

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

---

## Stage copy — the locked script (rev 19/08)

The first pass used **production labels** as on-screen titles — `ההבטחה`, `הכאב`,
`הרשמה · חשבון`. Those are names for the crew, not sentences for a viewer, and several
bodies were literally the storyboard's `scene:` direction. Replaced with viewer-facing
copy: the title makes a claim or asks the viewer's own question, and the two body lines
pay it off. Titles stay short (Frank Ruhl Libre 76px), bodies stay two lines at 30px.

| # | Title | Body line 1 | Body line 2 |
|---|---|---|---|
| 01 | החיסכון כבר שלכם | ההנחות האלה מגיעות לכם ממילא. | Lessley רק דואגת שלא תפספסו אותן. |
| 02 | עשרה מועדונים. אפס מעקב. | כרטיסים, קופונים והטבות שמתחלפים כל יום. | ובסוף החודש נשאר בדיוק אפס. |
| 03 | נרשמים בדקה | שם, אימייל, סיסמה — וזהו. | בשלב הזה עדיין לא נוצר חשבון. |
| 04 | קוד אחד, וזה רשמי | שש ספרות נשלחות לאימייל שלכם. | רק אחריהן החשבון באמת נוצר. |
| 05 | באילו אתם כבר חברים? | מסמנים את המועדונים שכבר יש לכם ביד. | מכאן ההתאמות מתחילות לעבוד. |
| 06 | כמה מחמיר לסנן? | רחב מציג יותר דילים, מחמיר רק את המדויקים. | ורואים את ההשפעה בזמן שבוחרים. |
| 07 | לקריאה בלבד | Lessley קוראת איפה קניתם — ותו לא. | היא לא יכולה להזיז שקל אחד. |
| 08 | עם סיסמה או בלי | סיסמה רגילה, או קוד חד-פעמי למייל. | ואם שכחתם — יש מסלול איפוס מלא. |
| 09 | ארבעה מסכים. זהו. | אופטימיזציה, תובנות, חם והמלצות. | התראות ופרופיל תמיד בהישג יד. |
| 10 | כמה תשלמו בפועל? | בוחרים חנות ומזינים את סכום העגלה. | המנוע בודק כל צירוף אפשרי. |
| 11 | ₪1,000 הפכו ל-₪700 | שלוש מאות שקלים, בלי לעשות כלום. | לא הערכה — דיל אמיתי, זמין עכשיו. |
| 12 | בלי אותיות קטנות | כל שקל של הנחה מוסבר צעד-צעד. | ורואים מאיזה מועדון בדיוק הוא הגיע. |
| 13 | כל הדילים במקום אחד | מסננים לפי חנות, קטגוריה או חיפוש חופשי. | וקוד הקופון מועתק בלחיצה. |
| 14 | כמה כבר חסכתם | לא תחזית ולא הערכה. | כסף שנחסך על קניות שבאמת ביצעתם. |
| 15 | לאן הכסף הולך | לפי קטגוריה, חנות, כרטיס ותקופה. | חמש שקופיות, תמונה אחת שלמה. |
| 16 | מה שווה עכשיו | בחירה אצורה מכל המועדונים שלכם. | לא מה שטרנדי — מה שבאמת משתלם. |
| 17 | לאיזה מועדון כדאי להצטרף | מדורג לפי החנויות שאתם קונים בהן. | Mastercard מכסה 10 מתוך 35 מהן. |
| 18 | מה פספסתם | הנחות שהיו זמינות ופשוט לא נוצלו. | וכל התאמה מסומנת ברמת ודאות. |
| 19 | מגיע אליכם לבד | כשהניתוח מסתיים, ההתראה קופצת. | בלי לרענן ובלי לחפש. |
| 20 | הכול בשליטתכם | מועדונים, רמת סינון וכרטיסים מחוברים. | והתנתקות שלא מוחקת כלום. |
| 21 | בטוח מהיסוד | מוצפן בהעברה, לקריאה בלבד, ניתן לביטול. | והמידע שלכם לעולם לא נמכר. |

Where a title or body is split across `<span>`s for a staggered entry, keep the animation
and re-split the new text across the same number of spans. Do not drop the stagger to make
the swap easier.

**Frames 11 and 12 carry no stage text.** They are the centred hero pair: frame 10 actively
clears the text panel inside its nudge-curve, and frame 11 opens on a full second of
stillness before the payoff. Their rows above are the line the *narration* delivers, not
copy to put on screen — putting a title back would undo a beat designed one frame earlier.
