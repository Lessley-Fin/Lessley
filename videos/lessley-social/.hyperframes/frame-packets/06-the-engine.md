# Frame packet: 06-the-engine

## Project inputs

- Project: /Users/dorhaba/Documents/Lessley/videos/lessley-social
- Design tokens: /Users/dorhaba/Documents/Lessley/videos/lessley-social/frame.md
- RULES_DIR: /Users/dorhaba/.claude/skills/hyperframes-animation/rules

## Assigned storyboard block

## Frame 6 — המנוע ⭐

- scene: the ten clubs orbit the cart; combinations are tested and the illegal ones fold and fall away until one survives
- voiceover: ""
- duration: 8s
- transition_in: blur-crossfade
- status: outline
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

## Selected blueprint: constellation-hub

# constellation-hub — Constellation / Hub + Satellites

**intent**: Labeled/iconned nodes spring into a ring/cluster around a center, then the shot resolves on the core — either by pushing the camera INTO the center (depth-of-field collapsing onto it) or by holding a hub mark while the satellites ORBIT it; the "everything connects to / sits around one center" beat.

**roles served**

- Hook (from `hook-cluster-push-in`): a constellation of tool/app nodes springs into a wide ring, then a sustained camera push-in with depth-of-field resolves on the inner core — "it connects everything / one hub for all your tools."
- Social_Proof (from `social-proof-orbit-ecosystem`): the product brand mark lands as the center hub and partner logos spring onto a ring and revolve around it — "plugs into / sits at the center of your stack."
- CTA (from `cta-orbit-collapse`): the ring resolves by COLLAPSE rather than a push-in — category icons drift around an empty central CTA, a cursor click implodes the orbit toward the click point, and the product demo springs OUT of that collapse as the answer (scope → choice → consequence → product).
- Social_Proof (from `proof-logo-chain`): a persistent center logo accrues proofs — its wordmark decodes, a claim ticker swaps, the logo glides to center, then avatars cascade into orbit with drawn connectors while partner logos scroll the bottom strip; four claims read as one statement.
- Social_Proof (from `scatter-drift-finisher`): the ecosystem beat as a
  static END CARD — a two-line serif `[headline]` is the center (no hub mark, no ring), `[~20 app
icons]` pop in scattered frame-wide in a quick stagger, then keep drifting very slowly OUTWARD
  to the end. "Connects to thousands of apps" said with count and spread, not geometry.

**duration**: 5–8s (Hook 5–6s · Social_Proof 5–8s · CTA orbit-collapse ~6s · Social_Proof
scatter-drift end card ~2.5s as a closing beat)

**shot structure**

Consolidated template — nodes ring a center, then one of two finishers resolves on the core.

- Scene 1 (0.0–~1.5s): `[bg]` (dark/space field, optionally slow-drifting diffused gradient blobs). `[primary nodes]` (circles carrying `[icon]` + label) SPRING-POP in (scale 0→1, ~1.15 elastic overshoot, staggered) arranged in a wide ring/cluster around an empty or marked center `[hub]`.
- Scene 2 (~0.7–2.5s, overlapping): smaller `[secondary nodes]` (platform / partner-logo chips) pop in staggered with the same elastic spring, filling the gaps; optional thin `[accent]` connector lines / orbit ring draw from hub→nodes. Camera holds.
- Scene 3 (~2.5–Xs, the resolve): see finisher variant below; lands and HOLDS on the magnified / orbited center to the end.

- Variant — Hook (push-in finisher): from Scene 3, a continuous smooth CAMERA PUSH-IN toward the center inner cluster — inner nodes scale up and stay sharp while outer nodes are pushed toward the edges and progressively BLUR (depth-of-field), background scales up smoothly; holds magnified on the core.
- Variant — Social_Proof (orbit finisher): the center `[brand mark]` snaps in via a quick 3D rotate that decelerates and settles; a thin `[accent]` orbit ring draws around it; `[N partner badges]` spring onto the ring (staggered overshoot) and revolve CLOCKWISE while staying upright, under a continuous slow camera ZOOM-OUT (ecosystem reveal).
- Variant — Social_Proof (optional type-push-through opener, prepended before Scene 1): centered `[headline]` types/slides in with a huge transparent-fill OUTLINE copy of the same words behind it; the outline text scales up exponentially toward camera (high-speed dolly / push-through), breaches the frame, then HARD-CUTS to the hub bg of Scene 1.
- Variant — Social_Proof (scatter-drift finisher, no ring): the center is a two-line serif
  `[headline]` building in place (not a mark); `[~20 app icons]` pop in SCATTERED across the whole
  frame in a quick stagger — no ring geometry, no connectors — then sustain a very slow outward
  drift to the end. Camera fully static: no push-in, no zoom-out; the "everything around one
  center" reads from the drift vectors pointing away from the headline. Often chained as the end
  card of a preceding UI beat (the prior card dissolves into it).

**motion vocabulary**: staggered elastic spring-pop node entrances (~1.15 overshoot); slow gradient-blob drift; connector-line / orbit-ring draw-on; 3D snap-rotate-settle on the hub mark; continuous camera push-in (inner sharp, outer depth-of-field blur, bg scale-up); clockwise orbital revolve of upright badges; continuous slow camera zoom-out (ecosystem reveal); optional outline-text push-through dolly entry. Scatter-drift finisher: frame-wide scattered icon pop-in (staggered, no ring); sustained slow
outward icon drift; in-place two-line serif headline build; static-frame hold to the end.

**rule mapping** (motion verb → `rules/<id>.md`)

- staggered spring-pop node entrances → `spring-pop-entrance` (elastic overshoot) + `gsap-effects` (stagger recipe); 3D-flip-in flavor → `orbit-3d-entry`
- ring / cluster layout of nodes around a center → `avatar-cloud-network` (nodes on an elliptical ring + SVG lines to a center)
- icons on the nodes → `svg-icon-enrichment`
- connector lines hub→node → `svg-path-draw`
- orbit-ring draw-on → `svg-path-draw`
- slow gradient-blob drift → `sine-wave-loop` (idle looped drift)
- 3D snap-rotate-settle on hub mark → `orbit-3d-entry` (3D-flip entry); technique CSS-3D
- clockwise orbital revolve of upright badges → `orbit-3d-entry` (continuous elliptical orbit); technique MotionPath
- camera push-in toward center → `multi-phase-camera` (PUSH-in) + `coordinate-target-zoom` (target the core)
- background scale-up during push-in → `multi-phase-camera`
- continuous slow zoom-out (ecosystem reveal) → `multi-phase-camera` (pull-back) / `coordinate-target-zoom`
- outline-text push-through dolly opener (Social_Proof) → `3d-text-depth-layers` (outline copy behind) + `multi-phase-camera` (push-through)
- depth-of-field blur on outer nodes during push-in → `depth-of-field-blur` (progressive DOF/focus-falloff blur on the off-center outer nodes while the inner core stays sharp)
- frame-wide scattered icon pop-in (no ring) → `spring-pop-entrance` (staggered group) +
  `gsap-effects` (stagger recipe); positions pre-baked scattered — NOT `avatar-cloud-network`'s
  elliptical ring
- sustained slow outward icon drift → `center-outward-expansion` (outward vectors, slow sustained
  register — drift targets sit slightly past the pop-in positions)
- in-place serif headline build → `gsap-effects` (staggered line/word reveal)

**camera modifier**: push-in-with-DOF (Hook) — `multi-phase-camera` PUSH-in targeted via `coordinate-target-zoom` onto the core; the focus-falloff blur half of it is backed by `depth-of-field-blur`. Orbit finisher (Social_Proof) — slow continuous zoom-out via `multi-phase-camera` (pull-back) while satellites revolve. Scatter-drift finisher (Social_Proof end card) — none: the frame never moves; the outward drift
is element-level.

## Selected motion rule: orbit-3d-entry

---
name: orbit-3d-entry
description: Elements flip in from 3D space then settle into continuous elliptical orbit around a focal point.
metadata:
  tags: orbit, 3d, flip, ellipse, circular, icon, entry, continuous
---

# Orbit with 3D Entry

Elements flip in from 3D space (`rotateX` + `rotateY` + negative `z`) then settle into a continuous elliptical orbit around a center label. Distinct from one-shot reveals — the orbit keeps running, driven by a 0→1 progress tween INSIDE the timeline (never rAF).

## How It Works

Per element, two phases: (1) a `back.out` flip from a hidden 3D orientation to flat — **in place at its orbital starting position** (see Critical Constraints); (2) a continuous orbit where `onUpdate` computes `x/y` from `cos/sin(initialAngle + p·2π)` on the ellipse. The stage needs `perspective` on the scene root and `preserve-3d` on stage + items, or the flip flattens to a 2D scale.

## Recipe

```html
<!-- inside a standard scene clip (hyperframes-core) -->
<div class="orbit-stage">
  <div class="orbit-item" data-angle="0">{glyph1}</div>
  <div class="orbit-item" data-angle="60">{glyph2}</div>
  <!-- … evenly-spaced angles … -->
  <div class="orbit-center">{centerLabel}</div>
</div>
```

```css
.scene-root {
  display: grid;
  place-items: center;
  perspective: 1800px; /* REQUIRED */
}
.orbit-stage {
  position: relative;
  display: grid;
  place-items: center;
  transform-style: preserve-3d;
}
.orbit-item {
  position: absolute;
  top: 50%;
  left: 50%;
  transform-style: preserve-3d;
  will-change: transform;
}
.orbit-center {
  position: relative;
  transform: translateZ(220px); /* wins paint order inside preserve-3d */
  z-index: 9999;
}
```

```js
const items = document.querySelectorAll(".orbit-item");
const RADIUS_Y = RADIUS_X * Y_TO_X_RATIO; // perspective-flattened ellipse

items.forEach((el, i) => {
  const a0 = (Number(el.dataset.angle) / 360) * Math.PI * 2;
  const startX = Math.cos(a0) * RADIUS_X;
  const startY = Math.sin(a0) * RADIUS_Y;

  // 1) Park at the orbital position, hidden — BEFORE any tween fires
  gsap.set(el, {
    xPercent: -50,
    yPercent: -50,
    x: startX,
    y: startY,
    rotateX: ROTATE_X_FROM,
    rotateY: ROTATE_Y_FROM,
    z: Z_FROM,
    opacity: 0,
    scale: SCALE_FROM,
  });

  // 2) Flip in IN PLACE — rotation/opacity/scale only, never translate
  tl.to(
    el,
    {
      rotateX: 0,
      rotateY: 0,
      z: 0,
      opacity: 1,
      scale: 1,
      duration: ENTRY_DUR,
      ease: `back.out(${FLIP_BACK})`,
    },
    i * STAGGER,
  );

  // 3) Continuous orbit — each item gets its OWN progress tween (own initialAngle)
  const orbit = { p: 0 };
  tl.to(
    orbit,
    {
      p: 1,
      duration: ORBIT_DURATION,
      ease: "none",
      onUpdate: () => {
        const a = a0 + orbit.p * Math.PI * 2;
        const x = Math.cos(a) * RADIUS_X;
        const y = Math.sin(a) * RADIUS_Y;
        // capped z-index band [1, 50] — see center-label clearance below
        el.style.zIndex = String(1 + Math.round(((y + RADIUS_Y) / (2 * RADIUS_Y)) * 49));
        el.style.transform = `translate(-50%, -50%) translate(${x}px, ${y}px)`;
      },
    },
    i * STAGGER + ENTRY_DUR,
  );
});

tl.from(
  ".orbit-center",
  { opacity: 0, scale: 0.6, duration: ENTRY_DUR, ease: `back.out(${CENTER_BACK})` },
  CENTER_FADE_AT,
);
```

## Variations

- **Collapse to center**: a final 1→0 driver multiplies both radii (and item scale) in `onUpdate` — the ring condenses into the center element; pairs with a CTA "click" igniting the collapse.
- **Tilted orbit plane**: `rotateX(25deg)` on `.orbit-stage` — items visibly arc through the plane.

## Values

| token                   | range                         | notes                                                               |
| ----------------------- | ----------------------------- | ------------------------------------------------------------------- |
| RADIUS_X                | 300–900px                     | must also clear the center label horizontally (see below)           |
| Y_TO_X_RATIO            | 0.4–0.7                       | keep < 1 — a tilted ring, not a frontal halo                        |
| ORBIT_DURATION          | 4–25s per revolution          | ≥ time on screen, or the tween ends and items freeze                |
| ENTRY_DUR               | 0.4–0.8s                      |                                                                     |
| STAGGER                 | 0.06–0.12s                    | below reads "popcorn", above reads plodding                         |
| FLIP_BACK / CENTER_BACK | 1.2–2.0 / 1.2–1.8             | calm the center pop if both fire close together                     |
| CENTER_FADE_AT          | after 2–4 items land          | too early competes; too late leaves a hole                          |
| ROTATE_X/Y_FROM, Z_FROM | ±60–120°, ±45–120°, −200…−400 | one consistent rotation direction across items; mixed signs = noise |
| SCALE_FROM              | 0.2–0.6                       |                                                                     |
| item count              | 4–12                          | fewer feels empty, more crowds the center                           |

## Critical Constraints

- **❗ Entry must flip IN PLACE at the orbital position, NOT at center** — `gsap.set` each item at `(cos(a0)·RADIUS_X, sin(a0)·RADIUS_Y)` with `opacity: 0` BEFORE adding tweens, then phase 1 animates only rotation/opacity/scale. A fromTo that keeps `x/y: 0` flips at the stage center, collides with the center label, then teleports to the orbit when phase 2 starts.
- **❗ Center-label clearance** — `z-index` alone is unreliable inside `preserve-3d` (paint order follows actual Z): push the label forward with `translateZ(220px)` + `z-index: 9999`, cap item z-index to `[1, 50]`, AND size the ring so items clear the label horizontally at every angle: `RADIUS_X × min|cos(θ)| ≥ L_w + I_w + breathing_room` (label/item half-widths; for 6 items the worst case is `cos(30°) ≈ 0.866`). A heavier wordmark needs a wider ring.
- **Each item gets its OWN orbit tween** — a shared `targets: ".orbit-item"` tween can't carry per-item `initialAngle`.
- **The center element is the headline** — the orbit is ornament; if it dominates, grow the center or fade the items down.

## See also

`center-outward-expansion` (burst entry; reversed driver = the collapse finish) · `cursor-click-ripple` (the click that triggers a collapse) · `depth-scatter-assemble` (3D entrance that resolves flat instead of orbiting).

## Selected motion rule: scale-swap-transition

---
name: scale-swap-transition
description: Coordinated shrink-out + spring pop-in morph-like transition between two elements — no SVG path interpolation needed.
metadata:
  tags: transition, morph, scale, swap, spring, pop
---

# Scale-Swap Transition

Simulates a "morph" between two DOM elements by overlapping exit and entrance scale animations. Lighter weight than [card-morph-anchor.md](card-morph-anchor.md) (which morphs container dimensions — use that for SHAPE changes; this rule is for SAME-shape state swaps) and easier than SVG path interpolation.

At a single trigger, two coordinated tweens fire:

1. **Outgoing**: scale `1.0 → EXIT_SCALE` + opacity `1 → 0`, fast `power2.in` (rushing away).
2. **Incoming**: scale `EXIT_SCALE → 1.0` + opacity `0 → 1`, `back.out(BOUNCE_FACTOR)` (arriving with weight).

A small `OVERLAP` window during which both are mid-tween creates the morph illusion; the incoming sits on top via z-index so the outgoing's fade-tail doesn't bleed through.

## Recipe

```html
<!-- Both cards position: absolute; inset: 0 in one fixed-size wrapper — same
     footprint, same transform-origin: 50% 50%. Incoming starts opacity: 0,
     transform: scale(EXIT_SCALE), z-index above the outgoing. -->
<div class="swap-wrap">
  <div class="card outgoing" id="outgoing">{outgoingIcon} {outgoingLabel}</div>
  <div class="card incoming" id="incoming">
    {incomingIcon} {incomingLabel}
    <div class="sub" id="sub">{incomingSubline}</div>
  </div>
</div>
```

```js
// Outgoing: shrink + fade fast
tl.to(
  "#outgoing",
  { scale: EXIT_SCALE, opacity: 0, duration: EXIT_DUR, ease: "power2.in" },
  TRIGGER,
);

// Incoming: pops in with overshoot, starting OVERLAP before the exit finishes
tl.to(
  "#incoming",
  { scale: 1.0, opacity: 1, duration: ENTER_DUR, ease: `back.out(${BOUNCE_FACTOR})` },
  TRIGGER + EXIT_DUR - OVERLAP,
);

// Inner content reveals AFTER the incoming settles
tl.fromTo(
  "#sub",
  { opacity: 0, y: SUB_REVEAL_Y_PX },
  { opacity: 1, y: 0, duration: SUB_REVEAL_DUR, ease: "power3.out" },
  TRIGGER + EXIT_DUR + SUB_REVEAL_DELAY,
);
```

## Variations

- **Delayed inner content reveal** — the classic pattern above: morph the container, then reveal inner text once it settles; the 0.2–0.4 s gap lets the eye land on the new shape before reading.
- **Triple swap (3-state cycle)** — chain A→B→C with triggers `TRIGGER_AB` / `TRIGGER_BC`; each transition is its own tween pair, the previous incoming becoming the next outgoing. State-evolution narratives (early → mid → final labels).
- **Color-shift transition (no scale)** — for a flat morph between same-shape states, drop the scale and keep opacity + a brief background hue tween; less dramatic, more product-UI tone.

## Values

| token            | range                                 | notes                                                                                                  |
| ---------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| TRIGGER          | ≥ outgoing settled + a presence-dwell | the outgoing must "land" before transforming                                                           |
| EXIT_DUR         | 0.3–0.5 s                             |                                                                                                        |
| ENTER_DUR        | 0.45–0.7 s                            | longer than `EXIT_DUR` so the overshoot can settle                                                     |
| OVERLAP          | 0.1–0.2 s                             | >0.3 s both are clearly visible together (no morph); <0.05 s leaves a visible empty gap                |
| EXIT_SCALE       | 0.6–0.8                               | smaller exits feel dramatic but risk reading as "vanish" instead of "morph"                            |
| BOUNCE_FACTOR    | 1.4 soft · 1.8 firm · 2.2 cartoony    |                                                                                                        |
| SUB_REVEAL_DELAY | 0.2–0.4 s                             | reveals during the morph compete with the swap for attention                                           |
| BRAND_REVEAL_AT  | < TRIGGER                             | context (brand, eyebrow) sets the stage early; revealed AT the swap it competes with the headline beat |

## Critical Constraints

- **Incoming z-index ABOVE outgoing** — otherwise the outgoing's fade-tail (opacity 0.3–0.5) bleeds through and double-exposes the frame.
- **Both elements share `transform-origin: 50% 50%`** — different origins make the morph read as one thing teleporting elsewhere.
- **Bouncy ease ONLY on the incoming** — outgoing `power2.in`, incoming `back.out`; reversed, the swap feels mechanical.
- **Both cards `position: absolute; inset: 0`** in the same fixed-size wrapper (sized to fit both states; the wrap never resizes).
- **Don't `display: none` the outgoing** after the fade — leave it at `opacity: 0` so layout doesn't reflow.
- **Inner content reveals after the container settles**; **climax dwell ≥ 1 s** after the final state + subline land.

## See also

`press-release-spring` (a button press TRIGGERS the swap — cause and effect) · `card-morph-anchor` (shape-changing alternative) · `reactive-displacement` (when the replacement should read as a causal collision) · `sine-wave-loop` (idle breathing on the final state).

## Selected motion rule: svg-path-draw

---
name: svg-path-draw
description: Animate SVG paths drawing progressively using stroke-dasharray and stroke-dashoffset.
metadata:
  tags: svg, stroke, draw, path, reveal, icon, vector
---

# SVG Path Draw

Reveals an SVG shape by animating its stroke as if a pen were tracing it. Two stroke properties together: **`stroke-dasharray = <pathLength>`** makes the entire path one dash; **`stroke-dashoffset`** starts at the path length (dash shifted fully out of view → invisible) and tweens to `0` (fully drawn). The length comes from the DOM API `path.getTotalLength()` — measured, never guessed.

Works on anything with a stroke: `<path>`, `<circle>`, `<rect>`, `<line>`, `<polyline>`, `<polygon>`, `<ellipse>`.

## Recipe

```html
<!-- inside a standard scene clip -->
<svg class="logo-mark" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <path id="bar-left" d="M 60 40 L 60 160" />
  <path id="bar-right" d="M 140 40 L 140 160" />
  <path id="bar-mid" d="M 60 100 L 140 100" />
</svg>
```

```css
.logo-mark path {
  fill: none; /* outline-only draw — a fill would appear immediately and ruin the reveal */
  stroke: {accentColor};
  stroke-width: 12;
  stroke-linecap: round; /* softer endpoints */
  stroke-linejoin: round;
}
```

```js
// Setup: measure each path and set its dash pattern. Real measured geometry, not a magic number.
document.querySelectorAll(".logo-mark path").forEach((p) => {
  const len = p.getTotalLength();
  p.style.strokeDasharray = `${len}`;
  p.style.strokeDashoffset = `${len}`;
});

// Stagger draws so the eye reads continuous motion — each segment starts at
// ~70-80% of the previous segment's duration, before it finishes.
tl.to(
  "#bar-left",
  { strokeDashoffset: 0, duration: SEGMENT_DRAW_DUR, ease: "power2.out" },
  SEG_1_START,
);
tl.to(
  "#bar-right",
  { strokeDashoffset: 0, duration: SEGMENT_DRAW_DUR, ease: "power2.out" },
  SEG_2_START,
);
tl.to(
  "#bar-mid",
  { strokeDashoffset: 0, duration: FINAL_SEGMENT_DUR, ease: "power2.out" },
  SEG_3_START,
);

// Companion wordmark fades in only after the last stroke settles.
tl.to(
  ".brand-line",
  { opacity: 1, duration: BRAND_FADE_DUR, ease: "power1.out" },
  BRAND_FADE_START,
);
```

## Variations

- **Ring starting at 12 o'clock** — `<circle>` / `<rect>` strokes start at 3 o'clock by default; rotate the element `-90deg` so a progress ring draws from the top:

```html
<circle
  cx="100"
  cy="100"
  r="60"
  id="ring"
  style="transform-origin: 100px 100px; transform: rotate(-90deg)"
/>
```

- **Linear (constant-speed) draw** — `ease: "none"` for a steady-rate "real pen" trace.
- **Draw then fill** — for filled shapes, tween `fillOpacity: 0 → 1` AFTER the stroke completes (requires `fill-opacity: 0` initially and a real `fill` in CSS):

```js
tl.to(
  "#path",
  { strokeDashoffset: 0, duration: SEGMENT_DRAW_DUR, ease: "power2.out" },
  SEG_1_START,
);
tl.to(
  "#path",
  { fillOpacity: 1, duration: FILL_FADE_DUR, ease: "power1.out" },
  SEG_1_START + SEGMENT_DRAW_DUR,
);
```

## Values

| token             | range                                   | notes                                                                                              |
| ----------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------- |
| SEGMENT_DRAW_DUR  | 0.3–0.8s                                | fast snap vs deliberate pen trace; >~1s feels sluggish for a logo reveal                           |
| FINAL_SEGMENT_DUR | 60–80% of SEGMENT_DRAW_DUR              | proportional to segment length — a short connector at full duration reads slower than its siblings |
| SEG_N_START       | previous start + 70–80% of its duration | reads as continuous motion, not N isolated animations                                              |
| SEG_1_START       | 0–0.4s                                  | a small ~0.2s lead-in lets the viewer settle before motion                                         |
| BRAND_FADE_START  | ≥ last stroke end (+ ~0.2s beat)        | earlier and the wordmark competes with the draw                                                    |
| BRAND_FADE_DUR    | 0.3–0.8s                                | snap (urgent) vs glide (premium)                                                                   |

Ease families are discrete choices: **stroke draws** use `power2.out` (a hand lifting at end of stroke) or `none` for constant speed — never `back.out` / `elastic.out` (pens don't bounce). **Fades** use `power1.out`.

## Critical Constraints

- **`fill: none`** for outline-only draws — otherwise the fill appears immediately.
- **Dasharray/dashoffset = the measured `getTotalLength()`**, set at setup; requires the SVG in the DOM (inline SVG is fine; a loaded `<image>` SVG is not).
- **Complex paths**: if `getTotalLength()` looks wrong, overestimate slightly (`len * 1.05`) — too large is invisible at animation start; too small clips the end.
- **Stagger multi-path draws at ~70–80%** of the previous segment's duration.
- **A drawn line must land on something.** When the path is a connector (rail, beam, underline, callout) rather than a shape, both endpoints must sit on real elements and the draw must do a job — reveal, route, validate, or emphasize. A stroke that only decorates empty space reads as filler; attach it or cut it.

## See also

`svg-icon-enrichment` (internal parts animate after the outline draws) · `counting-dynamic-scale` (stroke draws an icon while a number counts up) · `hacker-flip-3d` (logo draws, wordmark decodes beneath).
