---
format: 1080x1920
duration: 76s
message: "בנקאות פתוחה + מנוע האופטימיזציה — שני חיבורים שמהם נגזרות כל שאר היכולות"
arc: Mechanism-First Cascade — hook → pain → foundation 1 (open banking) → trust → foundation 2 (the optimizer) → capability cascade → CTA
audience: "צרכנים ישראלים שחברים בכמה מועדוני צרכנות ולא מצליחים לעקוב"
mode: collaborative
music: calm confident fintech underscore, steady mid-tempo pulse, restrained, clear downbeats
---

> **No narration.** `voiceover` is empty on every frame by design — the on-screen Hebrew
> is the narrator. Each frame's `onscreen:` lines in the prose are the reveal cues Step 4
> paces to the music's beat grid, exactly where a narrated video would pace to the voice.
> There is no `SCRIPT.md`. BGM only.
>
> **Ground rhythm.** Only two grounds exist (`bg` cream / `ground-dark` navy) and they swap
> by the signature circle wipe. The sequence is deliberate: cream for claims and payoffs,
> navy for pressure and machinery. Frames that flip ground use `blur-crossfade`.

## Video direction

Written once; every frame inherits it. Per-frame Scene lines carry only the delta.

**Palette system** (roles from `frame.md`, never invented):
`bg` cream is the ground for claims, payoffs and calm; `ground-dark` navy is the ground for
pressure and machinery. `primary` teal is the only accent — one per frame, on the focal.
`text` for headlines, `text-muted` for support; on navy those become `ground-dark-ink` /
`ground-dark-muted`. `payoff` gold is a **spend, not a colour**: Frames 1, 7 and 13 only.
Type by role — `h1`/`h2` are Frank Ruhl Libre 700 display; every ₪ figure and every label is
Heebo (800 tabular for figures).

**Motion grammar + reveal model.** Long-tail settles, `power3` default — smooth over bouncy;
no `back.out` / `bounce.out` / `elastic.out` anywhere. **There is no voiceover, so each
frame's `onscreen:` cues are the reveal clock**: cue 1 is what exists at t=0, and every later
cue reveals on its own beat, weighted into the back half of the frame. Nothing is ever dumped
at t=0. Because the cues ride the music instead of a voice, each cue lands on a downbeat of
the bed (~100 bpm, one bar ≈ 2.4s) — reveals feel scored rather than arbitrary.

**RTL is the motion default.** Staggers fire right→left, bars and the marker swipe grow from
the right edge, cascades enter from the right. This reverses the natural direction of every
rule cited below; the worker mirrors, never re-uses the LTR direction.

**Rhythm — held frames are allocated deliberately:** Frame 4 (the trust stamps hold still and
read), Frame 7 (a full beat of stillness before the gold pill lands — the climax earns it),
and Frame 13 (the lockup holds to the last frame). Everything else reveals across its cues.
During any hold the only sanctioned aliveness is low-amplitude **subtle jitter**
(`sine-wave-loop`); no breathing, no back-half pan or push.

**Caption band.** No captions are generated, but the bottom ~17% (≈326px) stays clear anyway
— it is the feed's own chrome zone on a 9:16 reel. All content plans into the top ~83%.

**Negative list — never appears:** emoji characters (no emoji font in the renderer — every
glyph is inline SVG); browser chrome, nav bars, scrollbars, real OS cursors; gradient text;
neon or purple-blue "AI" gradients; a third ground colour; gold outside Frames 1/7/13; any
invented club, store, or figure. Both motion failure modes are banned by name: **slideshow**
(everything on screen by ~25%, then frozen) and **screensaver** (elements floating
independently with no cause). And no `repeat`/`yoyo`, no `Math.random`, no `Date.now`, no CSS
`transition`/`@keyframes` for motion.


## Frame 1 — כמה מזה קיבלתם

- scene: ₪1,284 counts up in gold on cream, then the question lands beneath it
- voiceover: ""
- duration: 6s
- transition_in: cut
- status: animated
- src: compositions/frames/01-hook.html
- type: hook
- persuasion: Statistical proof + pain validation
- beat: curiosity + indignation
- ground: cream
- asset_candidates: assets/logo-without-name.svg — Lessley mark, small, bottom corner only
- handoff_out: the ₪1,284 figure — center x 540, y 820, scale 1.0, opacity 1, at rest

- blueprint: dataviz-countup (Adapt)
- focal: assets/logo-without-name.svg
- roles: logo-without-name.svg = supporting (small, bottom-right, enters last)
- sfx: impact-bass-1, sparkle

Adapt: keep the *cold-open on one exploding statistic* signature. The blueprint's icon burst
and camera push-through are dropped — vertical has no room for a scatter, and a push would
fight the count. The escalation comes from the figure's own value-scaled growth instead.
Scene 1 (0.0–2.2s): cream ground, empty. `₪1,284` alone, dead-center-upper-third, enters as a
**value-scaled counter** counting 0→1,284 while its type size grows with the value
(`counting-dynamic-scale`) in `payoff` gold, Heebo 800 tabular — Centered, the figure alone at
~55% of frame width. Nothing else exists yet.
Scene 2 (2.2–3.6s): the counter locks. `כבר היו שלכם` reveals beneath it **per-word, right→left**
(`dynamic-content-sequencing`) in `text-muted` — the figure holds still while the line arrives.
Scene 3 (3.6–5.2s): `כמה מזה באמת קיבלתם?` reveals per-word below, and a **marker highlight
sweep** draws right→left under `קיבלתם` in `primary` teal (`css-marker-patterns`) as the word
lands. Rule-of-thirds now: figure upper, question lower.
Scene 4 (5.2–6.0s): held read. The Lessley mark fades up small at the bottom-right. Everything
still; **subtle jitter** only (`sine-wave-loop`, low amplitude).

`onscreen:`
1. `₪1,284` — counts 0 → 1,284 in `payoff` gold, Heebo 800 tabular, huge.
2. `כבר היו שלכם` — lands under it, muted.
3. `כמה מזה באמת קיבלתם?` — the marker swipe hits `קיבלתם`.

narrativeRole: Opens on the money, not the product. The figure is real (the demo user's
actual 90-day saved total), and the question turns it from a boast into an accusation the
viewer answers privately.
keyMessage: The savings already belong to you — the only question is whether you collected them.

**Why gold here and nowhere else for 30 seconds:** this is a savings payoff, the one thing
`payoff` is rationed for. It does not reappear until Frame 7.

## Frame 2 — עשרה מועדונים, אפס מעקב

- scene: ten real club logos flood in as chips and crowd toward the center, each stamped ₪0
- voiceover: ""
- duration: 5s
- transition_in: blur-crossfade 0.32s
- status: animated
- src: compositions/frames/02-problem.html
- type: pain_point
- persuasion: Pain agitation by accumulation
- beat: overwhelm
- ground: navy
- asset_candidates: assets/mastercard_logo.jpg — Mastercard Israel; assets/topcash_logo.png — Isracard TopCash; assets/hever_giftcard_logo.jpg — Hever Gift Cards; assets/hever_teamim_logo.jpg — Hever טעמים; assets/paisplus_logo.jpg — PaisPlus; assets/paisplus_food_chains_logo.png — PaisPlus Food Chains; assets/paisplus_networks_logo.jpg — PaisPlus Networks; assets/hot_logo.png — HOT Israel; assets/swish_logo.png — Swish
- handoff_in: the ten chips arrive from the frame edges; the gold figure has already cleared

- blueprint: overwhelm-surround (Adapt)
- focal: assets/mastercard_logo.jpg
- roles: mastercard_logo.jpg = cutout (largest chip, arrives first) · topcash_logo.png, hever_giftcard_logo.jpg, hever_teamim_logo.jpg, paisplus_logo.jpg, paisplus_food_chains_logo.png, paisplus_networks_logo.jpg, hot_logo.png, swish_logo.png = supporting (the crowding field)
- sfx: pop, whoosh-short

Adapt: keep the *close-in-from-all-sides* signature — the accumulation and the claustrophobic
crowd. Dropped: the avatar morph (there is no character in this film) and the zoom-out variant.
The ten chips are the density markers, and each carries its own `₪0` stamp so the crowding
means something rather than just being busy.
Scene 1 (0.0–1.4s): navy ground. Three chips arrive from the right edge in a right→left
stagger, spring-settling on a long tail (`spring-pop-entrance`), scattered across the upper
two-thirds — layered-depth, 3 depth layers (blurred chips behind, sharp chips front).
Scene 2 (1.4–2.8s): `עשרה מועדונים.` reveals per-word, right→left (`dynamic-content-sequencing`)
across the center. Behind it the remaining seven chips keep arriving on the stagger — the line
and the flood run together, so the text is read *through* the crowd.
Scene 3 (2.8–4.2s): every chip's `₪0` stamp flips on in a fast cascade, then all ten chips
**expand-in toward the center** — the inverse of `center-outward-expansion`, closing the gap
around the frame's middle until the composition is genuinely tight.
Scene 4 (4.2–5.0s): `אפס מעקב.` slams in dead-center on the beat the crowding peaks
(`kinetic-beat-slam`), one hard word, chips pushed to the edges behind it. Held.

`onscreen:`
1. `עשרה מועדונים.` — arrives as the chips crowd.
2. `אפס מעקב.` — lands on the beat the crowding peaks.

narrativeRole: Validates why the answer to Frame 1's question is "almost none of it."
Not laziness — arithmetic. Ten memberships, changing daily, no human tracks that.
keyMessage: The problem isn't that you don't have the discounts. It's that you can't track them.

**Behatsdaa has no logo file** — render it as a type-only chip in the identical chip shape
so the field still counts to ten.

## Frame 3 — היסוד הראשון: בנקאות פתוחה

- scene: the connect button is pressed and real transactions stream into the phone, resolving into three stat cards
- voiceover: ""
- duration: 6s
- transition_in: zoom-through 0.34s
- status: animated
- src: compositions/frames/03-open-banking.html
- type: product_intro
- persuasion: Show-don't-tell proof
- beat: clarity
- ground: navy
- asset_candidates: assets/logo-without-name.svg — Lessley mark in the phone header
- handoff_out: the device — center x 540, y 1040, scale 1.0, opacity 1, at rest; it persists into Frame 4

- blueprint: agent-progress-theater (Reproduce)
- focal: assets/logo-without-name.svg
- roles: logo-without-name.svg = supporting (the phone's header mark)
- sfx: click-soft, typing, chime

Reproduce: the blueprint's shape maps cleanly — a single trigger beat hands the frame to the
machine, working-state theater runs, then the receipt cascades in and checks off. The device
is the carrier, so the trigger happens *inside* it and the receipt detaches *out* of it.
Scene 1 (0.0–1.5s): navy ground. The device rises into frame from below and settles at rest
(x 540, y 1040) on a long-tail settle; its screen shows the real banking-connect screen with
`חיבור בנקאות פתוחה` as the one teal button. Centered, device ~46% of frame width.
Scene 2 (1.5–2.6s): an **oversized cursor** enters from off-screen right, travels to the
button, and lands a **click with ripple** (`cursor-click-ripple`) — the recipe's own press
compression carries the button feedback. The click ignites everything after it.
Scene 3 (2.6–4.6s): transaction rows stream into the screen in a fast right→left cascade
(`dynamic-content-sequencing`) — real store names, real amounts. Three stat cards **detach out
of the phone**, scaling up ~1.8× into the open field above it (`card-morph-anchor`), and their
figures **count up** (the Frame 1 value-scaled counter): `142 עסקאות` · `₪5,630` · `3 חשבונות`. This is
the back-half reveal; nothing about it existed at t=0.
Scene 4 (4.6–6.0s): `Lessley רואה איפה באמת קניתם` reveals per-word right→left across the top
third, and the **marker sweep** lands under `באמת` (`css-marker-patterns`). Stream settles; held.

`onscreen:`
1. `חיבור בנקאות פתוחה` — the real button label; an oversized cursor presses it.
2. `142 עסקאות` · `₪5,630` · `3 חשבונות` — count up as the stream lands.
3. `Lessley רואה איפה באמת קניתם` — the swipe hits `באמת`.

narrativeRole: The first of the two foundations. Every competitor guesses from a catalogue;
this one reads the actual ledger. The transactions streaming in are the proof, not a claim.
keyMessage: It doesn't guess where you shop. It knows.

**The device enters here and is the film's carrier** — built once, handed across every
later cut at matched position and scale. It never resizes.

## Frame 4 — לקריאה בלבד

- scene: three guarantee stamps land in sequence over the phone, which dims behind them
- voiceover: ""
- duration: 6s
- transition_in: crossfade 0.28s
- status: animated
- src: compositions/frames/04-read-only.html
- type: benefit_highlight
- persuasion: Risk reversal
- beat: skepticism → peace of mind
- ground: navy
- asset_candidates:
- handoff_in: the device continues from Frame 3 at x 540, y 1040, scale 1.0, opacity 1 — it dims to 0.72 with a 2px defocus, it does not move
- handoff_out: the device — x 540, y 1040, scale 1.0, opacity 0.72, blur 2px, still

- blueprint: grid-card-assemble (Adapt)
- focal: —
- roles: — (typography and the carried device only; no candidates on this frame)
- sfx: ping, ping, ping

Adapt: keep the *staggered self-assembly into a held array* signature, but the array is three
guarantee stamps rather than a feature grid, and they assemble **over** the carried device
rather than replacing it — the phone must stay visible for the promise to be about *it*.
Scene 1 (0.0–1.2s): navy. The device is exactly where Frame 3 left it and does not move; it
**dims to ~72%** and takes a light 2px defocus — a static state, not a tween. It must still
read as the real app: dimmed further it becomes a featureless grey slab and the promise
stops being about THIS product so the foreground can own
the read. `לקריאה בלבד` reveals per-word right→left, large, upper third; the **marker sweep**
draws under it in teal (`css-marker-patterns`).
Scene 2 (1.2–3.6s): the three stamps land **one per bar**, right→left, each spring-settling on
a long tail (`spring-pop-entrance`) with a small SVG check **self-drawing** inside it
(`svg-path-draw`): `בנקאות פתוחה מוסדרת` → `גישה לקריאה בלבד` → `השליטה נשארת אצלכם`. Stacked
vertically, center band, each ~72% of frame width. One stamp per music bar is the whole pacing.
Scene 3 (3.6–4.8s): `היא לא יכולה להזיז שקל אחד.` reveals beneath the stack in `ground-dark-muted`.
Scene 4 (4.8–6.0s): **held frame** — allocated in Video direction. Nothing moves but
low-amplitude **subtle jitter** on the stamp stack (the Frame 1 jitter register). The stillness is the
point: this is the beat where a viewer decides whether to trust the product.

`onscreen:`
1. `לקריאה בלבד` — the headline; the swipe hits it.
2. `בנקאות פתוחה מוסדרת` · `גישה לקריאה בלבד` · `השליטה נשארת אצלכם` — the app's own real
   footer string, split into three stamps that land one per beat.
3. `היא לא יכולה להזיז שקל אחד.`

narrativeRole: The objection fires the instant a viewer hears "it reads my bank," so it is
answered in the same breath rather than saved for the end. Handling it here also frees the
close to be pure CTA.
keyMessage: Read-only, regulated, revocable — it can see, it cannot touch.

## Frame 5 — עגלה של ₪1,000

- scene: the optimizer form fills — store, cart total, max deals — and the button fires into the working state
- voiceover: ""
- duration: 5s
- transition_in: blur-crossfade 0.32s
- status: animated
- src: compositions/frames/05-optimizer-input.html
- type: feature_showcase
- persuasion: Concrete specificity
- beat: curiosity
- ground: cream
- asset_candidates:
- handoff_in: the device brightens back from opacity 0.72 to 1.0 in place at x 540, y 1040, scale 1.0
- handoff_out: the device — x 540, y 1040, scale 1.0, opacity 1; the `משלבים דילים…` spinner is still running at the cut

- blueprint: cursor-ui-demo (Reproduce)
- focal: —
- roles: — (the carried device and its reconstructed optimizer screen; no candidates)
- sfx: typing, click-soft

Reproduce: a visible cursor drives a reconstructed UI through real state changes, on a locked
stage where the element swaps do the camera work. Exactly this beat.
Scene 1 (0.0–1.0s): ground flips to cream behind the device via the **circle wipe**; the device
brightens from 45% back to full in place (no move, no rescale). Its screen is the real
optimizer form. Centered, device ~46% of frame.
Scene 2 (1.0–2.2s): the cursor moves to the store field; `FOX - פוקס` **types in with a caret**
(`discrete-text-sequence` + `context-sensitive-cursor`), right→left.
Scene 3 (2.2–3.2s): the cursor drops to `מחיר כולל ₪` and `₪1,000` types in; then the
`מקסימום דילים בשילוב` selector steps to `3 דילים` — a discrete token swap, not a fade
(`discrete-text-sequence`).
Scene 4 (3.2–4.2s): the cursor lands on `מציאת המחירים הטובים ביותר`; the button
**compresses and springs** (`press-release-spring`) and its label hard-cuts to `משלבים דילים…`
with the working state running.
Scene 5 (4.2–5.0s): `כמה תשלמו בפועל?` reveals per-word right→left above the device. The
spinner **keeps running through the cut** — the question is deliberately unanswered here.

`onscreen:`
1. `FOX - פוקס` types into the store field.
2. `₪1,000` types into `מחיר כולל ₪`.
3. `מקסימום דילים בשילוב: 3 דילים`
4. `מציאת המחירים הטובים ביותר` — pressed → `משלבים דילים…`
5. `כמה תשלמו בפועל?`

narrativeRole: Opens the second foundation with a concrete, checkable cart rather than an
abstraction. The spinner deliberately does not resolve here — it hands the unresolved
question to Frame 6.
keyMessage: A real store, a real cart, a real question.

## Frame 6 — המנוע ⭐

- scene: the ten clubs orbit the cart; combinations are tested and the illegal ones fold and fall away until one survives
- voiceover: ""
- duration: 8s
- transition_in: blur-crossfade 0.32s
- status: animated
- src: compositions/frames/06-the-engine.html
- type: feature_showcase
- persuasion: Mechanism reveal — showing the work is the differentiator
- beat: intrigue → inevitability
- ground: navy
- asset_candidates: assets/mastercard_logo.jpg — Mastercard Israel; assets/topcash_logo.png — Isracard TopCash; assets/hever_giftcard_logo.jpg — Hever Gift Cards, the surviving deal; assets/paisplus_food_chains_logo.png — PaisPlus Food Chains, rejected on exclusive_group; assets/paisplus_networks_logo.jpg — PaisPlus Networks, rejected on stackable_with_giftcards
- handoff_in: the device recedes to opacity 0 as the orbit takes the frame; the cart figure ₪1,000 survives the cut at center x 540, y 960, scale 1.0

- blueprint: constellation-hub (Adapt)
- focal: assets/hever_giftcard_logo.jpg
- roles: hever_giftcard_logo.jpg = cutout (the survivor — ends alone at center) · mastercard_logo.jpg, topcash_logo.png, paisplus_food_chains_logo.png, paisplus_networks_logo.jpg = supporting (the tested candidates; the two PaisPlus marks are the ones that visibly fail)
- sfx: riser, whoosh-short, impact-bass-1

Adapt: keep the *nodes spring into a ring around a center, then the orbit resolves on the core*
signature. What changes is why the orbit collapses: not a click, but **elimination**. Each
rejected node folds and falls out of the ring carrying its real reason, so the collapse is the
engine's reasoning made visible. This is the film's most differentiating shot and gets its own
riser.
Scene 1 (0.0–1.6s): navy. `₪1,000` holds dead-center — it survived the cut from Frame 5 at the
same coordinates. Club marks **flip in from 3D space and settle into an elliptical orbit**
around it (`orbit-3d-entry`), staggered right→left. Layered-depth; far-side nodes carry a
static depth blur so the ring reads as real space.
Scene 2 (1.6–3.0s): `המנוע בודק כל צירוף אפשרי` reveals per-word right→left in the upper third.
Beneath it, faint SVG connector lines **self-draw** between pairs of orbiting nodes
(`svg-path-draw`, run on straight chords between orbit positions) — the engine testing combinations, one pair per beat.
Scene 3 (3.0–5.4s): elimination. Three combinations fail in sequence, one per bar: the connector
snaps, a small label hard-cuts in beside the pair — `קבוצה בלעדית` on the two PaisPlus marks,
`לא ניתן לשלב` on the giftcard clash — and both nodes **fold and fall out of frame** with a
directional velocity smear. The ring visibly thins.
Scene 4 (5.4–7.0s): only `hever_giftcard_logo` is left. It **scale-swaps into the center**
against the shrinking remains of the ring (`scale-swap-transition`) and locks beside `₪1,000`.
Scene 5 (7.0–8.0s): `רוב הצירופים לא חוקיים.` / `הוא יודע בדיוק אילו.` reveal on two beats, the
**marker sweep** under `חוקיים` (the Frame 1 marker recipe). Held — the ring is gone, one node stands.

`onscreen:`
1. `המנוע בודק כל צירוף אפשרי` — as the orbit spins up.
2. Rejection labels flash on the folding combinations — `לא ניתן לשלב` · `קבוצה בלעדית` —
   each fold is a real engine rule, not decoration.
3. `רוב הצירופים לא חוקיים.` / `הוא יודע בדיוק אילו.` — the swipe hits `חוקיים`.

narrativeRole: The single most differentiating frame in the video. A coupon list cannot do
this. The rejections carry the argument — anyone can show three discounts stacking; only a
real engine can show which stacks the rules forbid.
keyMessage: It isn't a list of deals. It's a solver.

**Truth constraint:** the two PaisPlus FOX deals are both `giftcard_discount`, one carries
`stackable_with_giftcards: false`, and they share `exclusive_group: paisplus:chit-5001`.
The real engine therefore returns a **one-deal** stack. The frame must show exactly that —
never a three-deal stack the engine would reject.

## Frame 7 — ₪1,000 הפכו ל-₪700 ⭐

- scene: the old total strikes through, the new one counts down, and the gold savings pill springs in
- voiceover: ""
- duration: 7s
- transition_in: blur-crossfade 0.32s
- status: animated
- src: compositions/frames/07-payoff.html
- type: benefit_highlight
- persuasion: Negative contrast (before/after) + statistical proof
- beat: relief → triumph
- ground: cream
- asset_candidates: assets/hever_giftcard_logo.jpg — Hever Gift Cards, the club that won the stack
- handoff_in: ₪1,000 arrives at the position it held in Frame 6 — x 540, y 960, scale 1.0, opacity 1 — then the strike-through draws from the right

- blueprint: dataviz-countup (Adapt)
- focal: assets/hever_giftcard_logo.jpg
- roles: hever_giftcard_logo.jpg = supporting (the club chip on the winning-stack card header)
- sfx: impact-bass-1, sparkle

Adapt: keep the *land on one hero metric* signature. The count **descends** rather than climbs —
the value falling is the good news here — and the blueprint's camera push-through is replaced by
a full beat of stillness before the payoff, per the Video direction's held-frame allocation.
Scene 1 (0.0–1.4s): ground flips to cream via the **circle wipe**. `₪1,000` arrives at the exact
center it held in Frame 6 — a matched handoff, no jump. The winning-stack card assembles
underneath it: teal band across the card top carrying `השילוב הטוב ביותר` and
`FOX - פוקס · דיל אחד הופעל`, with the Hever chip at its right. Centered, card ~76% of frame.
Scene 2 (1.4–2.6s): a **strike-through draws right→left** across `₪1,000`
(`css-marker-patterns`) — the line is drawn, not faded on.
Scene 3 (2.6–4.2s): `אתם משלמים` labels, and `₪700` **counts down** from 1,000 in `primary`
teal, Heebo 800 tabular, its size scaling with the change (`counting-dynamic-scale`). The struck
`₪1,000` stays visible above it — the contrast is the argument.
Scene 4 (4.2–5.2s): **held.** One full beat, everything still. No reveal, no jitter yet. This
silence is deliberate and is what makes the next beat land.
Scene 5 (5.2–7.0s): `חיסכון ₪300 (30%)` **spring-pops** in as a gold pill
(`spring-pop-entrance`, long-tail settle — no overshoot), and an **ambient glow blooms** behind
it once (`ambient-glow-bloom`). `לא הערכה — דיל אמיתי, זמין עכשיו.` reveals beneath in
`text-muted`. Settles into the hold; **subtle jitter** only.

`onscreen:`
1. `השילוב הטוב ביותר` — the real card title, with `FOX - פוקס · דיל אחד הופעל` beneath.
2. `₪1,000` struck through → `אתם משלמים` `₪700` counts down.
3. `חיסכון ₪300 (30%)` — gold pill springs in.
4. `לא הערכה — דיל אמיתי, זמין עכשיו.`

narrativeRole: Pays off everything Frames 5–6 set up, and pays it in the viewer's own
currency. One second of stillness before the pill lands — the payoff needs the silence.
keyMessage: Three hundred shekels, for doing nothing.

**Gold's second and last appearance before the CTA.** Frame 1 spent it; this frame spends
it again. Nothing between them may use it.

## Frame 8 — בלי אותיות קטנות

- scene: the stack steps unfold one row at a time, each row explaining where a shekel went
- voiceover: ""
- duration: 5s
- transition_in: crossfade 0.28s
- status: animated
- src: compositions/frames/08-how-it-stacks.html
- type: feature_showcase
- persuasion: Transparency as proof
- beat: trust
- ground: cream
- asset_candidates: assets/hever_giftcard_logo.jpg — the club on the stack step row
- handoff_in: the winning-stack card continues from Frame 7 at x 540, y 700, scale 1.0, opacity 1, and slides up 180px to make room for the rows

- blueprint: grid-card-assemble (Reproduce)
- focal: assets/hever_giftcard_logo.jpg
- roles: hever_giftcard_logo.jpg = supporting (the club mark on the stack-step row)
- sfx: click-soft, ping

Reproduce: a vertical list that accumulates row by row and holds. The disclosure *is* an
accumulating list, so the blueprint needs no adaptation.
Scene 1 (0.0–1.0s): cream. The winning-stack card continues from Frame 7 unchanged, then
**slides up 180px** on a slow-fast-slow three-phase move (`nudge-curve`) to open room beneath
it. `איך זה מצטבר` reveals as the disclosure label on the vacated line.
Scene 2 (1.0–3.4s): three rows cascade in right→left, one per beat
(`dynamic-content-sequencing`), each a mint-tinted step row: `ההנחה חלה על ₪1,000` ·
`משלמים עליו ₪700` · `נשאר לתשלום ₪700`. The last row's previous balance renders struck through.
A small chevron **self-draws** between consecutive rows (`svg-path-draw`). Full-width strip,
rows ~82% of frame width.
Scene 3 (3.4–4.4s): `כל שקל מוסבר צעד-צעד.` reveals beneath the stack in `text-muted`.
Scene 4 (4.4–5.0s): held read — the whole arithmetic visible at once, which is the point.

`onscreen:`
1. `איך זה מצטבר` — the real disclosure label.
2. Rows cascade: `ההנחה חלה על ₪1,000` · `משלמים עליו ₪700` · `נשאר לתשלום ₪700`.
3. `כל שקל מוסבר צעד-צעד.`

narrativeRole: Converts the payoff from a claim into an audit. A number you can take apart
is a number you believe — and no competitor exposes its arithmetic.
keyMessage: You can check the maths yourself.

## Frame 9 — כל הדילים במקום אחד

- scene: deal cards filter down under a search, and a coupon code copies with one press
- voiceover: ""
- duration: 5s
- transition_in: zoom-through 0.34s
- status: animated
- src: compositions/frames/09-deal-finder.html
- type: feature_showcase
- persuasion: Friction reduction
- beat: ease
- ground: navy
- asset_candidates: assets/hot_logo.png — HOT Israel on a deal card; assets/swish_logo.png — Swish on a deal card; assets/topcash_logo.png — Isracard TopCash on a deal card
- handoff_in: clean cut into the cascade section — nothing carries; the circle wipe re-establishes the navy ground

- blueprint: cursor-ui-demo (Adapt)
- focal: assets/hot_logo.png
- roles: hot_logo.png = cutout (the deal card that survives the filter) · swish_logo.png, topcash_logo.png = supporting (cards that filter away)
- sfx: whoosh-short, click-soft, ping

Adapt: keep the *cursor drives real state changes, landing on the action control* signature.
Adapted for the cascade's doubled pace: the cursor does one thing only — the copy press — and
the filtering happens as a card cascade rather than a click-through, because there is no time
for a multi-step workflow here.
Scene 1 (0.0–1.2s): the **circle wipe** re-establishes navy — this is a section boundary and
the ground change announces it. `כל הדילים שלכם במקום אחד` reveals per-word right→left, upper
third. Deal cards are already streaming in behind it as a loose stack.
Scene 2 (1.2–2.4s): three filter chips hard-cut on right→left — `חנות` · `קטגוריה` ·
`חיפוש חופשי` (`discrete-text-sequence`) — and on the third, the card stack **filters down**:
non-matching cards fall away with a directional velocity smear, leaving the HOT
card alone and scaled up in the center.
Scene 3 (2.4–3.8s): the cursor enters, lands on `העתקה`; the button **compresses and springs** on a long tail and the label hard-cuts to `הועתק` with a check **self-drawing** beside
it (`svg-path-draw`).
Scene 4 (3.8–5.0s): `קוד קופון בלחיצה.` reveals beneath, **marker sweep** under `בלחיצה`
(`css-marker-patterns`). Held.

`onscreen:`
1. `כל הדילים שלכם במקום אחד`
2. `חנות · קטגוריה · חיפוש חופשי` — the three filters, as chips.
3. `העתקה` pressed → `הועתק` — the swipe hits `בלחיצה` in `קוד קופון בלחיצה.`

narrativeRole: Opens the cascade. From here the pace roughly doubles: each frame is a
capability, and the accumulating breadth is itself the argument.
keyMessage: Every club you belong to, searchable in one place.

## Frame 10 — הכסף שלכם, מפוענח

- scene: the insights carousel fans out as five slides, with the savings hero above them
- voiceover: ""
- duration: 6s
- transition_in: blur-crossfade 0.32s
- status: animated
- src: compositions/frames/10-insights.html
- type: benefit_highlight
- persuasion: Value stacking
- beat: clarity + control
- ground: cream
- asset_candidates:
- handoff_out: the ₪1,284 savings-hero figure — x 540, y 620, scale 1.0, opacity 1

- blueprint: grid-card-assemble (Adapt)
- focal: —
- roles: — (typography and reconstructed insight cards; no candidates on this frame)
- sfx: chime, pop

Adapt: keep the *self-assembling array that enumerates breadth at once* signature. The array
fans as a **carousel of five slide cards** rather than a flat grid, because that is the real
shape of the insights screen and because a fan reads at vertical scale where a 5-up grid does
not.
Scene 1 (0.0–1.2s): ground flips to cream via the **circle wipe**. `הכסף שלכם, מפוענח` reveals
per-word right→left, large, upper third — the app's own page title.
Scene 2 (1.2–2.8s): the savings hero card assembles beneath it — navy card, `נחסך עם Lessley`
in small letterspaced caps, and `₪1,284` **counting up** in white
(`counting-dynamic-scale`). Beneath it `30 הימים האחרונים · 10 מועדונים`. This is Frame 1's
figure returning; the count is the callback.
Scene 3 (2.8–5.0s): five slide cards **expand outward from a clustered center**
(`center-outward-expansion`) into an overlapping fan across the lower band, right→left, one per
half-bar: `סקירה כללית` · `קטגוריות` · `חנויות מובילות` · `עסקאות` · `חשבונות`. Layered-depth,
3 depth layers, each card carrying a small self-drawn SVG glyph (`svg-path-draw`).
Scene 4 (5.0–6.0s): the fan locks. Held read; **subtle jitter** only.

`onscreen:`
1. `הכסף שלכם, מפוענח` — the app's own page title.
2. `נחסך עם Lessley` `₪1,284` · `30 הימים האחרונים · 10 מועדונים`
3. Five slide cards fan: `סקירה כללית` · `קטגוריות` · `חנויות מובילות` · `עסקאות` · `חשבונות`.

narrativeRole: Closes the loop opened in Frame 1 — the ₪1,284 returns, now explained rather
than asserted. This is only possible because of foundation 1; a coupon app has no ledger to
decode.
keyMessage: Not a forecast. Money saved on purchases you actually made.

## Frame 11 — לאיזה מועדון כדאי להצטרף

- scene: club match rows rank with right-filling progress bars, then the missed-savings figure lands
- voiceover: ""
- duration: 6s
- transition_in: crossfade 0.28s
- status: animated
- src: compositions/frames/11-recommendations.html
- type: feature_showcase
- persuasion: Future pacing + loss aversion
- beat: FOMO → motivation
- ground: cream
- asset_candidates: assets/mastercard_logo.jpg — Mastercard Israel, the top match; assets/topcash_logo.png — Isracard TopCash, the runner-up
- handoff_in: the ₪1,284 figure from Frame 10 shrinks to 0.4 scale and clears to the top-right corner as the rows arrive

- blueprint: grid-card-assemble (Adapt)
- focal: assets/mastercard_logo.jpg
- roles: mastercard_logo.jpg = cutout (the top-ranked match row) · topcash_logo.png = supporting (the runner-up row)
- sfx: pop, ping, impact-bass-1

Adapt: keep the *ranked vertical list that accumulates and steps* signature, extended with the
blueprint's optional **bar fill** so the ranking is shown rather than asserted. The bars fill
from the **right** — the RTL reversal in the Video direction.
Scene 1 (0.0–1.2s): cream. Frame 10's `₪1,284` shrinks to ~0.4 scale and clears to the top-right
corner as a persistent anchor (`scale-swap-transition`). `לאיזה מועדון כדאי להצטרף` reveals
per-word right→left; **marker sweep** under `כדאי` (`css-marker-patterns`).
Scene 2 (1.2–3.0s): two ranked rows cascade in, one per bar (`dynamic-content-sequencing`). Row
one: Mastercard mark, `Mastercard Israel`, `10/35 חנויות תואמות`, and a `29%` badge; its
**progress bar fills from the right** (`stat-bars-and-fills`). Row two follows with
`Isracard TopCash · 10% · 31/300` and a visibly shorter fill. Full-width strip, rows ~84%.
Scene 3 (3.0–4.4s): the missed-savings card **detaches upward** out of the list (the Frame 3 detach
recipe), scaling up: `₪340 שפספסתם ב-FOX - פוקס` with the figure **counting up** in `text` (the Frame 1 counter) — deliberately *not* gold; this is a loss, not a payoff.
Scene 4 (4.4–6.0s): three certainty chips hard-cut on right→left beneath it — `מדויקת` ·
`חזקה` · `דומה` (the Frame 5 hard-cut register). Held.

`onscreen:`
1. `לאיזה מועדון כדאי להצטרף` — the swipe hits `כדאי`.
2. `Mastercard Israel · 29% · 10/35 חנויות תואמות` — bar fills from the right.
   `Isracard TopCash · 10% · 31/300` beneath it.
3. `₪340 שפספסתם ב-FOX - פוקס`
4. Three certainty chips: `מדויקת` · `חזקה` · `דומה`.

narrativeRole: The most complete proof of the thesis in the whole video — recommending a
club you are *not yet* in requires knowing where you shop, and ranking it requires the
matching engine. Both foundations, in one frame.
keyMessage: It tells you which club to join next, ranked by where you actually shop.

## Frame 12 — מגיע אליכם לבד

- scene: a live toast drops in over the phone and the notification feed fills behind it
- voiceover: ""
- duration: 5s
- transition_in: blur-crossfade 0.32s
- status: animated
- src: compositions/frames/12-notifications.html
- type: benefit_highlight
- persuasion: Friction reduction
- beat: ease + inevitability
- ground: navy
- asset_candidates: assets/logo-without-name.svg — Lessley mark on the toast
- handoff_out: the device — x 540, y 1000, scale 1.0, opacity 1, holding still for the CTA wipe

- blueprint: agent-progress-theater (Adapt)
- focal: assets/logo-without-name.svg
- roles: logo-without-name.svg = supporting (the mark on the live toast)
- sfx: notification, pop

Adapt: keep the *machine finishes working and the receipt arrives* signature, compressed to its
second half — the working state already happened, off-screen and unattended, which is precisely
the claim. So the frame opens on the arrival.
Scene 1 (0.0–1.0s): the **circle wipe** returns navy. The device is back at rest, screen dim,
nothing happening — one beat of genuine stillness so the interruption reads as an interruption.
Scene 2 (1.0–2.2s): the toast **drops in from the top edge** and settles on a long tail
(`spring-pop-entrance`), overlapping the device: Lessley mark, `הניתוח מוכן`, timestamp. It is
the only lit thing in frame.
Scene 3 (2.2–3.6s): four badges cascade in behind it right→left, one per half-bar
(`dynamic-content-sequencing`): `ניתוח` · `מועדונים` · `דיל` · `מערכת`, each a filled pill.
Scene 4 (3.6–5.0s): `מגיע אליכם לבד.` reveals per-word across the upper third with the
**marker sweep** under `לבד` (`css-marker-patterns`), then `בלי לרענן. בלי לחפש.` in
`ground-dark-muted` beneath. Held.

`onscreen:`
1. `הניתוח מוכן` — the real notification title, arriving as a live toast.
2. Badges stack behind it: `ניתוח` · `מועדונים` · `דיל` · `מערכת`.
3. `בלי לרענן. בלי לחפש.` — the swipe hits `לבד` in `מגיע אליכם לבד.`

narrativeRole: Closes the cascade on autonomy — the product works while you don't. It is
also the last capability that only the two foundations make possible.
keyMessage: You don't go looking. It finds you.

## Frame 13 — טייס אוטומטי פיננסי

- scene: the ten club logos collapse inward into a single card that becomes the Lessley lockup
- voiceover: ""
- duration: 6s
- transition_in: zoom-through 0.34s
- status: animated
- src: compositions/frames/13-cta.html
- type: cta
- persuasion: Value consolidation + low-risk ask
- beat: confidence → urgency-to-act
- ground: navy
- asset_candidates: assets/logo-without-name.svg — the closing mark; assets/mastercard_logo.jpg; assets/topcash_logo.png; assets/hever_giftcard_logo.jpg; assets/paisplus_logo.jpg; assets/hot_logo.png; assets/swish_logo.png — the ten clubs collapsing inward
- handoff_in: the device from Frame 12 is swallowed by the circle wipe; the club logos re-enter from the frame edges

- blueprint: logo-assemble-lockup (Adapt)
- focal: assets/logo-without-name.svg
- roles: logo-without-name.svg = cutout (the resolved lockup — the wordmark beside it is LIVE
  TYPE in white, not the with-name asset: that asset's lettering is dark navy, drawn for a
  light ground, and it all but vanishes on this frame's dark ground) · mastercard_logo.jpg, topcash_logo.png, hever_giftcard_logo.jpg, paisplus_logo.jpg, hot_logo.png, swish_logo.png = supporting (the ten satellites that collapse into it)
- sfx: whoosh-short, impact-bass-1, chime

Adapt: keep the *satellites clear and the mark resolves into a centered lockup, extended to the
CTA* signature. The satellites are the same ten chips that opened the pain in Frame 2 — so the
collapse is a structural rhyme, not decoration: the thing that overwhelmed the viewer at 0:06
becomes the single card they now hold.
Scene 1 (0.0–1.6s): the **circle wipe** takes navy and swallows the device. The ten club chips
re-enter from the frame edges to the same scattered positions they held in Frame 2 — the
viewer recognises the arrangement before they can name why.
Scene 2 (1.6–3.2s): the chips **collapse inward toward one center** — the inverse of
`center-outward-expansion` — converging on a single card that **scale-swaps** into existence as
they arrive (`scale-swap-transition`), each chip streaking slightly on the way in.
Scene 3 (3.2–4.4s): the card resolves into the mark-plus-wordmark lockup, its rule
**self-drawing** as it settles (`svg-path-draw`). Centered, ~62% of frame width.
Scene 4 (4.4–5.4s): `טייס אוטומטי פיננסי לכל רכישה` reveals per-word right→left beneath the
lockup; then `התחילו בחינם` **spring-pops** in as a solid teal pill (the Frame 2 entrance) with
`https://lessley.cs.colman.ac.il` beneath it in Heebo 600, forced LTR inside its own isolation
span so the bidi algorithm cannot reorder it against the surrounding Hebrew.
Scene 5 (5.4–6.0s): **held to the final frame.** This is the video's only real exit — every
other frame exits through its injected transition. Fully still; **subtle jitter** only.

`onscreen:`
1. Ten club chips converge and collapse into one card.
2. `Lessley` lockup resolves.
3. `טייס אוטומטי פיננסי לכל רכישה`
4. `התחילו בחינם` + `https://lessley.cs.colman.ac.il`

narrativeRole: Restates the whole video in one image — ten fragmented memberships become
one thing you check. The CTA is low-risk by design because the ask follows a video that
spent its whole length proving the mechanism.
keyMessage: Ten clubs, one autopilot. Free to start.

**The CTA URL is confirmed:** `https://lessley.cs.colman.ac.il` (user, 21/08). The repository's
`lessley.example.com` is a placeholder and must never appear on screen. Render the URL in
Heebo 600 at LTR direction inside its own isolation span so the bidi algorithm cannot
reorder it against the surrounding Hebrew.
