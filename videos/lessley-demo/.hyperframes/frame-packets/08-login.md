# Frame packet: 08-login

## Project inputs

- Project: /Users/dorhaba/Documents/Lessley/videos/lessley-demo
- Design truth: /Users/dorhaba/Documents/Lessley/videos/lessley-demo/frame.md
- RULES_DIR: /Users/dorhaba/Documents/Lessley/.agents/skills/hyperframes-animation/rules

## Assigned storyboard block

## Frame 8 — התחברות

- scene: מסך ההתחברות; מעבר בין "סיסמה" ל"קוד באימייל", ורמז למסלול איפוס הסיסמה
- duration: 15s
- transition_in: cut
- status: built
- blueprint: cursor-ui-demo
- rules: theme-crossfade-morph, cursor-click-ripple
- voiceover: "בכניסות הבאות יש שתי דרכים: סיסמה רגילה, או קוד חד-פעמי למייל — בלי סיסמה בכלל. ואם שכחתם — מסלול איפוס מלא: מייל, קוד, סיסמה חדשה."
- src: compositions/frames/08-login.html

`theme-crossfade-morph` מחליף את גוף הטופס תחת עוגן קבוע (הכותרת "ברוכים השבים"),
כך שהמעבר בין שני מצבי ההתחברות קורא כהחלפה ולא כמסך חדש.

## Selected blueprint: cursor-ui-demo

# cursor-ui-demo — Cursor-Driven UI Demo

**intent**: A visible custom cursor drives a real (reconstructed) app UI through clicks / hovers / drags so the screen changes state shot-to-shot, while the camera chases each interaction — the product surface is the subject and the cursor is the actor.

**roles served**

- Product_Intro (from `product-intro-cursor-ui-demo`): first look at the product surface — the cursor sweeps/hovers to \_introduce\* the app and reveal what it is, landing on a hovered hero element or freshly-popped result. Light, exploratory; backdrop steps colors as it goes.
- Key_Feature (from `key-feature-cursor-ui-demo`): one specific multi-step workflow demonstrated \_end-to-end\* (edit / configure / select across 2–4 discrete beats), each beat a real edit the UI responds to live, landing locked on the primary action button or the produced result.
- Key_Feature (from `workflow-approve-press`): an agency / confirmation workflow framed by a cockpit of 3D-tilted flanks — a step list ticks pending → active → complete (a snap state machine, CSS responding to `[data-state]`), and a flank button takes the PRESS as the payoff (its color flips to success, a checkmark stamps). The click is the climax, not a passing gesture.
- Key_Feature (from `cursor-app-state-tour`): the static-stage STATE TOUR — the cursor drives a reconstructed app through 2–4 discrete feature states on a LOCKED frame; every scene change is a click-triggered element swap/scale (modal springs from center, side panel slides in from the right edge, settings hard-swap, table populates, node-graph builds), never a real camera move; optional `[title card]` Scene 0 in front and a `[brand end beat]` behind.
- Key_Feature (from `drag-field-onto-document`): the DRAG-DROP journey — one continuous zoom-breathing shot of a document workspace: the cursor drags a ghosted `[field chip]` from an inputs sidebar onto the page, drop-snaps it into a placed field, a modal/typing beat completes it, and the placed element is adjusted in close-up before the cursor heads to the `[Finish/CTA]`.
- Product_Intro: the low-event BROWSE — the cursor roams ONE clean page state and the filter controls answer with slight hover updates; no typed input, no title beats, and the shot may end mid-roam.
- Product_Intro (from `hover-inspect-run`): the HOVER-INSPECT run — a click SPAWNS a labeled `[toolbar]`, the camera zooms out from a tight crop to the full page, then the cursor sweeps `[page elements]` while a floating `[inspector panel]` TRACKS the cursor, outline-highlighting and content-snapping per hovered element. (The slice's three-beat dark title prelude, scenes 1–3, belongs to `titlecard-reveal`, not here.)
- Hook: the ambient MULTI-CURSOR canvas — several labeled `[teammate cursors]` work a design canvas simultaneously (grab-drag-drop of components between mockups, recolor/identity swaps on drop) while the canvas group translate-PANS within a static frame and a `[headline]` builds word-group by word-group over the demo; the live workshop itself is the hook. One continuous beat, no cuts, no camera.
- Benefits (from `ui-demo-text-interlude-ui-demo`): the demo|text|demo SANDWICH — two static-stage demo beats of this blueprint bridge through a full-screen kinetic/title interlude and back (cursor acts, UI answers, all "zoom" element scale); the interlude beat is `kinetic-type-beats` material, and the sandwich itself is sequencing above the single-shot unit.

**duration**: 4.0–12.9s (Key_Feature 4.0–12.9s — the mined state tours run long, 10.4–12.9s, and the drag-drop journeys 9.8–10.6s, against the original 4.0–7.3s set; Product_Intro 4.5–9.3s — the low-event browse sets the 4.5s floor; Hook ~6.5s; the Benefits demo|text|demo sandwich totals 11.6–12.8s with each demo half ~4–5s)

**shot structure** (a `[product UI surface]` — fixed app window, dashboard/editor, parallax `[content card]` stack, or a `[container object/icon]` — centered over `[bg color/gradient]`, shown `[flat]` or `[3D-isometric]`; a custom `[brand-colored cursor with icon]` is the protagonist and the camera servos to whatever it touches; UI responds _live_ and in sync with each cursor action. Two role-tuned tempos fold in — Product_Intro **sweeps to introduce**, Key_Feature **performs a workflow** — and the camera spans a spectrum: the full CHASE, one continuous zoom-breathe, or a fully LOCKED static stage where the UI itself does all the moving.)

- **Scene 1 (0.0–~Xs) — surface establishes + first touch.** The `[product UI surface]` arrives centered over `[bg color/gradient]` — either it is simply present (fixed window / dashboard / editor), a 3D-parallax stack of `[content cards]`, or a `[container object/icon]` that FLIES IN with a 3D tumble and settles. The custom `[cursor]` enters. The cursor performs the FIRST action on `[cursor target 1]` and the UI responds live in the same beat. Camera holds or begins a slow push-in toward the acted-on region.
  - _Variant — Product_Intro_: low-commitment first touch — cursor HOVERS/sweeps a control or SWEEP-HIGHLIGHTS a field to `[accent color]`, OR the `[container]` fans open. An optional label/title fades/morphs onto the surface. The point is to _show the surface exists_ and is touchable.
  - _Variant — Key_Feature_: a concrete edit — cursor DRAGS a scrollbar / TYPES into a field / DRAGS a handle, and the UI responds materially (`[scroll]` / value climbs / region resizes). If the surface opened in `[3D-isometric]`, it may snap perspective-FLAT here to read the workflow.
  - _Variant — Key_Feature (static-stage tour)_: an optional Scene 0 — `[title card / kinetic brand word]` on a flat field — hard-cuts or window-SCALES-UP into the surface; the `[app UI]` is fully present from the first frame and the cursor enters and glides to the first control. The camera is LOCKED from the start and stays locked.
  - _Variant — Hook (ambient multi-cursor)_: no single protagonist — several labeled `[teammate cursors]` are already at work across `[N mockups]` on a design canvas; the canvas group translate-PANS within the static frame while a `[headline]` builds word-group by word-group over the top. One continuous beat, no cuts.

- **Scene 2 (~Xs–~Ys) — camera chases to the next interaction (the engine).** The camera MOVES to the next target — push-in + pan / whip-pan / pan-down to `[cursor target k]` — and the cursor performs action k as the UI updates live. Each beat is a discrete interaction connected by a fast camera move; the surface's inner content SWAPS per interaction.
  - _Variant — Product_Intro_: navigation is exploratory — a slow camera pan + depth-of-field FOCUS-PULL across a parallax `[content card]` stack, or the `[container]` fanning into `[N option/content cards]` that SPRING to position. As content swaps, the supporting backdrop STEPS its color (`[bg step 1]` → step 2 → …). Typically one or two such moves.
  - _Variant — Key_Feature_: repeat for `[2–4 beats total]`, each a distinct operation the UI answers — counter COUNTS UP, `[pill/swatch]` SELECTS, a modal SLIDES UP and TYPES — connected by whip-pans / progressive zoom. The workflow visibly advances toward a result.
  - _Variant — Key_Feature (static-stage tour)_: the camera never moves — every beat is a click-triggered ELEMENT response: a modal SPRINGS/scales up from center, a `[side detail panel]` SLIDES in from the right edge (a second panel may slide over the first), hamburger→sidebar slide-open, a settings panel HARD-swaps its content, a dropdown fills, a `[table]` populates row-by-row, a formula types into a cell and the range populates on enter, a type-to-filter list live-collapses, a `[block]` pops into the canvas, a node-graph BUILDS (cards + connecting lines radiate from center), a hover drops a `[popover]` below a tag. Any "zoom" is element scale of the UI only.
  - _Variant — Key_Feature (drag-drop)_: the cursor GRABS a `[field chip]` from an `[inputs sidebar]`, drags a semi-transparent GHOST across the page, and drops it — it SNAPS into a placed field with bounding box + corner handles; a completion beat follows (a `[modal]` springs up over the dimmed document, a name types letter-by-letter while a live `[cursive preview]` builds per keystroke, confirm click). The whole clip rides one continuous zoom-BREATHING arc (slow zoom-out / gentle zoom-in / final zoom-out) instead of discrete camera beats.
  - _Variant — Product_Intro (hover-inspect)_: the cursor's first click SPAWNS a labeled `[toolbar]`, the camera zooms OUT from a tight crop to the full page, then the cursor sweeps `[page elements]` — each hovered element gets an outline and a floating `[inspector panel]` TRACKS the cursor, its content snapping per element.

- **Scene 3 (~Ys–end) — payoff state, camera settles, HOLD.** The cursor lands on its final target and the screen reaches the payoff state; the camera comes to rest (static) and holds.
  - _Variant — Product_Intro_: the cursor HOVERS the hero element — a `[content card]` SCALES UP on hover, a node gets an `[Available]`-style pill, or a `[result card]` POPS/springs in — the "here's the product" payoff. Settles static, holds.
  - _Variant — Key_Feature_: locked close-up on the OUTCOME — cursor lands on the `[primary action button: Export / Save / Reimburse]` and a `[hover backdrop / highlight]` SPRING-pops in (the climax is the action button / produced result). Holds.
  - _Variant — Key_Feature (static-stage tour)_: optional detachable end beat — `[brand text beat / icon-ring lockup / end stat card]` — or the cursor simply comes to REST on the next target and holds (006_claudeai ends with the cursor on a panel's close X, the panel never closing).
  - _Variant — Key_Feature (drag-drop)_: close-up on the placed element ADJUSTED — a corner-handle drag proportionally resizes it — then the cursor sweeps toward the `[Finish / CTA]` as the clip ends.
  - _Variant — browse / hover-inspect_: no payoff lock at all — the shot ends MID-demo, cursor still roaming (browse and hover-inspect modes).

**motion vocabulary**: cursor-driven click / hover / sweep-highlight / drag / type; per-interaction live UI response (scroll, value climb, region resize, content swap); camera push-in + pan / whip-pan / pan-down servoing to each target; coordinate zoom onto the acted region; press-and-ripple on a clicked control; button press-compress; screen-state swap shot-to-shot; card fan-out to corners (spring); 3D container fly-in & tumble-settle; perspective-flatten (3D→2D snap); paginated/stepped backdrop color advance; depth-of-field focus-pull across a parallax card stack; counter count-up; pill/swatch select; modal slide-up + typing; label/title morph between states; UI-keyword highlight glow; terminal hover-scale or result-card pop-in; spring hover-backdrop on the final action button; hard panel swap (no easing); side detail panel slide-in from the right edge (second panel over the first); hamburger→sidebar slide-open; hover popover drop below a tag; element-scale fake zoom (UI window scales in/out on click, camera locked); table populates row-by-row; formula typed into a cell + instant cell-range populate on enter; fill-handle drag auto-fill down rows; type-to-filter list live-collapse; dropdown fill on click; block/element pop-in to canvas; node-graph build (cards + connecting lines radiate from center); character-by-character auto-typing with blinking caret; window scale-up with settle; ghost-chip drag (grip dots + icon) across the page; drop-snap into a placed field with bounding box + corner handles + trash icon; modal spring-up over a dimming document; letter-by-letter typing with a live cursive preview building per keystroke; corner-handle drag with proportional resize; continuous zoom-breathing single shot (zoom-out / zoom-in / zoom-out arcs); cursor sweep toward the CTA at clip end; multiple labeled collaborative cursors moving independently; cursor grab-drag-drop of components between mockups; element recolor/identity swap on drop; canvas-group translate-pan within a static frame; headline building word-group by word-group over the demo; hover-triggered micro content/sidebar update; click spawns a labeled toolbar; floating inspector panel tracking the cursor with per-element content snap; per-element hover outline highlight; motion-blur window fly-in; tight-crop open then zoom-out to full page; brand icon-ring end beat; 3D end-card float on the hold.

**rule mapping**

- viewport follows the cursor / camera servos to whatever it touches (primary) → `camera-cursor-tracking`
- cursor moves to a target, presses, emits a ripple (the click itself — primary interaction primitive) → `cursor-click-ripple`
- screen-state swap shot-to-shot (surface inner content changes between beats) → `scale-swap-transition`
- camera push-in + pan / whip-pan / pan-down to the next target → `viewport-change` (pan/zoom across the UI)
- sequencing the chase into discrete interaction beats → `multi-phase-camera`
- zoom onto the specific acted-on UI region → `coordinate-target-zoom`
- cursor icon/state changing with context (e.g. pointer↔grab over a draggable handle) → `context-sensitive-cursor`
- which content appears per beat / step-by-step UI state progression / per-interaction swaps → `dynamic-content-sequencing`
- sweep-highlight a field, highlight a UI keyword to `[accent color]` → `asr-keyword-glow` (keyword glow on the touched element)
- clicked button compresses on press, springs back on release → `press-release-spring`
- cursor + button compress together on a heavier press → `physics-press-reaction`
- panel/card morphs between two states (e.g. card → expanded card, surface state A → B) → `card-morph-anchor`
- terminal hover-scale, `[result card]` pop-in, spring hover-backdrop on the final action button → `spring-pop-entrance`
- card fan-out to corners / option cards springing to position → `split-tilt-cards` (fan/spread into tilted positions) + `spring-pop-entrance` (the spring settle)
- 3D-parallax content-card stack as the surface; UI shown 3D-isometric → `3d-page-scroll` (UI as a tilted scrolling/parallax card)
- node gets an `[Available]`-style pill / tracked badge appears on an element → `ai-tracking-box`
- counter / value count-up as the UI responds → `counting-dynamic-scale`
- a result bar / number FILLS as the workflow's outcome → `stat-bars-and-fills`
- a live `[video]` screen-capture clip used as the surface → technique: video compositing
- perspective-flatten (3D-isometric → flat 2D snap) and the 3D-isometric tilt itself → technique: CSS-3D (no dedicated rule; the tilt/flatten transform is a CSS-3D primitive)
- camera settles static on the payoff and HOLDS → (settle phase of `spring-pop-entrance` on the payoff element; the static hold itself needs no rule)
- 3D container/object fly-in & tumble-settle → `depth-scatter-assemble` (free-tumbling 3D object/container entrance that flies in and tumble-settles; `orbit-3d-entry` only orbits a flat element into place)
- depth-of-field focus-pull across the parallax card stack → `depth-of-field-blur` (rack-focus / DoF blur transition between near and far cards; `3d-page-scroll` supplies the tilted parallax stack and `viewport-change` the pan)
- paginated/stepped backdrop color advance synced to interactions (`[bg step 1]`→step 2→…) → `discrete-text-sequence` (discrete state stepping, here applied to a background-color state rather than text)
- modal slide-up + in-modal typing as one combined beat → `card-morph-anchor` / `scale-swap-transition` (the panel slide-in) + `discrete-text-sequence` (the in-modal typed text)
- element-scale fake zoom — the UI window scales, camera locked (static-stage tour) → `coordinate-target-zoom` (applied to the surface wrapper rather than the world)
- side detail panel slide-in from the right edge / hamburger→sidebar slide-open / hover popover drop → `card-morph-anchor` / `scale-swap-transition` (the panel arrival) + `dynamic-content-sequencing` (which content each panel shows per beat)
- hard panel swap / in-panel content snapping through states / hover-triggered micro update / type-to-filter live-collapse / element identity swap on drop → `dynamic-content-sequencing`
- table populates row-by-row / fill-handle auto-fill cascading down rows / log rows cascade in → `waterfall-entry`
- formula typed into a cell / character-by-character auto-typing with blinking caret / letter-by-letter typed name → `discrete-text-sequence` + `context-sensitive-cursor` (the caret)
- node-graph build (cards + connecting lines radiate from center) → `center-outward-expansion` (the cards) + `svg-path-draw` (the connecting lines draw)
- click spawns a labeled toolbar / dropdown fills on click / drop-snap settle of the placed field / window scale-up with settle → `spring-pop-entrance`
- modal spring-up over a dimming document → `spring-pop-entrance` (the modal) + `depth-of-field-blur` (the document dim/blur beneath)
- ghost-chip drag-and-drop / cursor grab-drag of components between mockups / fill-handle drag / corner-handle resize drag → `cursor-drag` (`cursor-click-ripple` covers move+click only)
- floating inspector panel TRACKS the cursor, content snapping per element → `ai-tracking-box` (the per-frame follow mechanics, restyled as an inspector panel) + `dynamic-content-sequencing` (the per-element content)
- live cursive preview building per typed keystroke → `svg-path-draw` (progressive stroke reveal keyed to typing progress)
- continuous zoom-breathing single shot (drag-drop variant) → `multi-phase-camera` (pull-back / focus / push phases + micro-drift)
- motion-blur window fly-in / tight-crop open then zoom-out to full page → `motion-blur-streak` (the fly-in) + `viewport-change` (the zoom-out)
- multiple labeled collaborative cursors moving independently → `multi-cursor-choreography` (N labeled independent cursor actors; the single-actor cursor rules assume one)
- canvas-group translate-pan within a static frame → `viewport-change` (the `.world` translate realizes the pan; semantically the camera stays locked)
- headline builds word-group by word-group over the demo → `waterfall-entry`
- brand icon-ring end beat → `svg-path-draw` (the ring) + `spring-pop-entrance` (the lockup)
- 3D end-card float on the hold → `sine-wave-loop` — CAUTION: motion-doctrine bans idle wobble; prefer a settle-and-hold

**camera modifier**: The defining motion is the camera CHASE — the viewport follows the cursor from target to target via `camera-cursor-tracking` (primary), realized as concrete push-in + pan / whip-pan / pan-down moves under `viewport-change`, sequenced into discrete interaction beats by `multi-phase-camera`, with each beat's destination targeted via `coordinate-target-zoom` (zoom to the acted-on region). Product_Intro biases toward a slow, exploratory pan + focus-pull that sweeps the surface; Key_Feature biases toward snappier whip-pans / progressive zoom that march through the workflow and lock static on the action button. This camera-servo-to-cursor is what separates the blueprint from hands-off camera scrolls (dataviz-scroll-reveal) and static device/window tours. The golden set widens this into a spectrum. At one pole the **static-stage state tour** (now the largest member set) LOCKS the camera for the entire clip and lets the UI itself do all the moving — panel slide-ins, element-scale fake zooms, content snaps — with the cursor alone carrying the eye. The **drag-drop** variant replaces discrete chase beats with ONE continuous zoom-breathing arc under `multi-phase-camera`. The **hover-inspect** variant inverts the push-in: a tight-crop open zooms OUT to the full page before the cursor sweep. Pick the pole per brief — chase for workflow marches, locked stage for dense reconstructed dashboards, a single breathe for one-document journeys. With the locked pole absorbed, what separates this blueprint from `device-surface-showcase` is the CURSOR-as-actor, not the camera: a fully static tour still belongs here as long as a visible cursor drives every state change.

## Selected motion rule: theme-crossfade-morph

---
name: theme-crossfade-morph
description: Whole-theme in-place morph under a fixed anchor — background, typography, corner radii, icons, chrome and logos all blend simultaneously (~0.3s) through N pre-styled skins while one anchor element never moves. Recipe = stacked full layers + opacity crossfade, anchor rendered once on top. Seek-safe by construction.
metadata:
  tags: theme, skin, crossfade, morph, anchor, reskin, cycle, ui, stacked-layers
---

# Theme Crossfade Morph

The whole world re-skins while one thing holds still. A composer box cycles through four IDE themes; a checkout widget flips through brand skins — background, typography, corner radii, toolbar icons, footer logos all change **at once**, in place, in ~0.3s, N times — and through every flip one anchor element (the prompt string, the widget layout, the wordmark) **never moves**. The anchor's stillness is the rhetorical claim: _everything changes, this doesn't._

Boundary: [card-morph-anchor.md](card-morph-anchor.md) morphs **one container** between two shots — its dimensions, radius, and surface tween continuously. This rule re-skins an **entire scene** through **N discrete states**: nothing tweens property-by-property (fonts, icons, and logos can't interpolate); the "morph" is a fast simultaneous crossfade of complete pre-styled layers. ([scale-swap-transition.md](scale-swap-transition.md) swaps an element at center; here the surroundings swap and the element holds.)

## How It Works

1. **One skin = one complete layer.** Each theme state is a fully pre-styled, full-bleed layer (`position: absolute; inset: 0`) containing everything that changes: background, shell/chrome, toolbar icons, footer logos, typography. All `N_SKINS` layers exist in the DOM from `t=0`, stacked; skin 0 starts visible, the rest at `opacity: 0`.
2. **The morph is a crossfade.** At each boundary, two opposing opacity tweens run at the same timeline position over `MORPH_DUR` (~0.3s): outgoing `1 → 0`, incoming `0 → 1`. Because both layers are complete, every property "blends" simultaneously for free — including the un-tweenable ones (font families, icon glyphs, logos), which read as morphing precisely because everything else is mid-blend around them.
3. **The anchor renders once, on top.** The element that must not move lives in its own layer above all skins and is **excluded from every skin layer**. No transforms, no re-parenting, no per-skin restyle.
4. **Windows are precomputed.** `T_k = CYCLE_START + k × (SKIN_HOLD + MORPH_DUR)`. Steady cadence by default; hold the final skin longest when it's the resolve.

The only animated property is `opacity` — which is why this rule is seek-safe with zero special machinery.

## Recipe

```html
<!-- inside a standard scene clip (hyperframes-core) -->
<div class="theme-stage">
  <!-- One complete pre-styled layer per skin; skin-0 visible at t=0 -->
  <div class="skin skin-0"><div class="shell">…terminal chrome, mono type, footer badge…</div></div>
  <div class="skin skin-1">
    <div class="shell">…rounded composer, sans type, toolbar pills, logo…</div>
  </div>
  <div class="skin skin-2"><div class="shell">…dark shell, its own chrome and footer…</div></div>

  <!-- The anchor: rendered ONCE, above every skin. It never moves. -->
  <div class="anchor" id="anchor">{anchorText}</div>
</div>
```

```css
.theme-stage {
  position: absolute;
  inset: 0;
}
.skin {
  position: absolute;
  inset: 0;
  opacity: 0;
  /* Each skin fully self-styled: its own background, fonts, radii,
     icons, chrome, logos. Nothing inherited across skins. */
}
.skin-0 {
  opacity: 1; /* the opening state — matches the timeline's fromTo */
}
.shell {
  /* CRITICAL: shared geometry. The shell box (and any element that
     "persists" across skins — toolbar row, footer row) sits at the SAME
     coordinates in every skin, so mid-blend frames read as one UI
     changing clothes, not two UIs ghosting. */
  position: absolute;
  left: SHELL_LEFT;
  top: SHELL_TOP;
  width: SHELL_WIDTH;
  height: SHELL_HEIGHT;
}
.anchor {
  position: absolute;
  z-index: 10; /* above every skin */
  left: ANCHOR_LEFT;
  top: ANCHOR_TOP;
  /* No transforms, no transitions — the stillness is load-bearing. */
}
```

```js
const skins = gsap.utils.toArray(".skin");

// Boundary k→k+1 at T_k: outgoing fades down as incoming fades up —
// ONE simultaneous crossfade, everything blends at once.
skins.forEach((skin, k) => {
  if (k === 0) return; // skin-0 is the opening state
  const at = CYCLE_START + k * (SKIN_HOLD + MORPH_DUR);
  tl.fromTo(skin, { opacity: 0 }, { opacity: 1, duration: MORPH_DUR, ease: "power2.inOut" }, at);
  tl.to(
    skins[k - 1],
    { opacity: 0, duration: MORPH_DUR, ease: "power2.inOut" },
    at, // same position — the blend is simultaneous, never sequential
  );
});

// The anchor gets NO tweens. Its absence from the timeline is the point.
```

## Variations

- **Anchor-typography reskin (per-layer copies)** — when the anchor's own type treatment must change with the theme (mono in the terminal skin, sans in the editor skin), each skin carries its own copy of the anchor at **pixel-identical geometry** and there is no separate top layer; the invariant shifts from "one element" to "one geometry." Verify the copies overlay exactly (screenshot two skins at 50% opacity) — a 2px baseline drift reads as the anchor flinching, which breaks the whole claim.
- **Skin-cycle tour with logo relay** — a large brand logo outside the anchored shell crossfades **in the same windows** as the skins (logo k with skin k, same `MORPH_DUR`). The paired swap sells "same product, every brand."
- **Washout finale** — after the last skin, a final low-key layer (faint dot-grid, blueprint wash) fades in while the last shell drops to ~0.25 opacity — the cycle resolves into a held diagram of itself. One extra window; the anchor may fade with the shell or hold full-strength.
- **Emphasis brake** — steady cadence for `N−1` skins, then hold the final skin 2–3× `SKIN_HOLD`; the cycle demonstrates breadth, the brake lands the resolve. Precompute the hold array; don't drift the cadence without cause.

## Values

| token           | range                                       | notes                                                                                                |
| --------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| N_SKINS         | 3–5                                         | two is a before/after (consider `card-morph-anchor`); past five the cycle pads                       |
| SKIN_HOLD       | 0.8–1.5s                                    | long enough to register the logo/footer identity, short enough to keep the churn rhetorical          |
| MORPH_DUR       | 0.25–0.4s, ~0.3s canonical                  | faster reads as a hard cut; slower reads as a mushy dissolve with lingering double-exposure          |
| CYCLE_START     | ≥ anchor settle + a beat                    | after the anchor and skin-0 have fully registered                                                    |
| SHELL geometry  | —                                           | shell / toolbar / footer coordinates identical across skins; contents inside the slots differ freely |
| ANCHOR position | —                                           | identical to the pixel across the scene (per-layer form: identical in every skin)                    |
| washout / brake | shell ~0.2–0.3 opacity; hold 2–3× SKIN_HOLD | —                                                                                                    |

## Critical Constraints

- **The anchor never moves.** No transforms, no opacity dips, no re-parenting, no restyle — the contrast between total churn and total stillness is the entire device; one flinch and the shot becomes a slideshow.
- **Nothing tweens but `opacity`** — no `borderRadius` / `background` tweens; radii and colors change by being different in the next layer. Visibility via `opacity` only, never `display` / `visibility` toggles (they can't blend mid-fade).
- **Pixel-align the shared geometry** — mid-blend both skins are partially visible; aligned shells read as one UI changing clothes, misaligned shells ghost into two UIs.
- **Pre-style everything** — each skin is complete and static; no class toggling, no runtime restyle mid-tween.
- **Outgoing and incoming tweens share one timeline position** — a staggered blend flashes the stage background between skins.
- **Adjacent windows only** — skin k crossfades with k+1, never k+2; at no frame are three skins partially visible.
- **Camera static — always.** A push-in on top of a theme cycle destroys the stillness that makes the anchor read.
- **Hard cuts are the cheaper sibling** — if the states should _snap_, that's `discrete-text-sequence` territory; the ~0.3s blend is specifically the "morph" read.

## See also

`context-sensitive-cursor` (caret color switches at each `T_k`) · `discrete-text-sequence` (type the anchor first; or the hard-cut alternative) · `card-morph-anchor` (the single-container sibling) · `spring-pop-entrance` (the lockup that joins the anchor at the resolve) · `sine-wave-loop` (drifting field under the cycle — never on the anchor).

## Selected motion rule: cursor-click-ripple

---
name: cursor-click-ripple
description: Animated mouse cursor moves to target, clicks with scale depression and expanding ripple rings.
metadata:
  tags: cursor, click, ripple, interaction, mouse, button
---

# Cursor Click Ripple

An animated cursor moves to a target element, performs a click with visual depression, and emits expanding ripple rings from the click point. Three sequential phases on one timeline: **move** (eased translation to the target's center) → **click** (scale depression on cursor + target together, yoyo back) → **ripple** (1–3 staggered rings expand and fade from the click point). This is a _point event at one location_ — a sustained hold across space is [cursor-drag.md](cursor-drag.md).

## Recipe

```html
<button class="target-button">{ctaLabel}</button>
<div class="cursor"><!-- arrow SVG, positioned at the entry corner --></div>
<!-- Rings live in DOM from t=0 at the click-target CENTER, scale 0 + opacity 0 -->
<div class="ripple ripple-1"></div>
<div class="ripple ripple-2"></div>
<div class="ripple ripple-3"></div>
```

```css
.ripple {
  position: absolute;
  left: 50%;
  top: 50%; /* click-target center */
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 2px solid {rippleColor};
  transform: translate(-50%, -50%) scale(0);
  opacity: 0;
  pointer-events: none;
}
```

```js
// Phase 1 — Move: eased, not linear
tl.to(".cursor", { x: TARGET_X, y: TARGET_Y, duration: MOVE_DUR, ease: MOVE_EASE }, 0);

// Phase 2 — Click: cursor + target depress together, then return
tl.to(
  ".cursor",
  { scale: CURSOR_PRESS_SCALE, duration: PRESS_DUR, ease: "power2.in", yoyo: true, repeat: 1 },
  CLICK_AT,
);
tl.to(
  ".target-button",
  { scale: TARGET_PRESS_SCALE, duration: PRESS_DUR, ease: "power2.in", yoyo: true, repeat: 1 },
  CLICK_AT,
);

// Phase 3 — Ripple burst, N rings staggered from the click point
tl.set([".ripple-1", ".ripple-2", ".ripple-3"], { opacity: 1 }, RIPPLE_AT);
tl.to(
  [".ripple-1", ".ripple-2", ".ripple-3"],
  {
    scale: RIPPLE_SCALE,
    opacity: 0,
    duration: RIPPLE_DUR,
    ease: RIPPLE_EASE,
    stagger: RIPPLE_STAGGER,
    immediateRender: false, // holds scale 0 / opacity 0 until the click moment
  },
  RIPPLE_AT,
);
```

## Variations

- **Single ring** — one `.ripple`, no stagger; more elegant when the rest of the scene is busy.
- **Keyframed attack-decay** — a `keyframes` block ramps opacity 0 → peak → 0 across the duration; a clearer "energy radiates and dissipates" envelope.
- **Multi-ring expanding pulse** — 3 rings at 0.08 s stagger when the click is the scene's climactic moment.

## Values

| token                       | range                       | notes                                                                                                                                  |
| --------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| MOVE_DUR                    | 0.4–1.0 s                   | short darts; long reads as a "considered click." Must end before CLICK_AT or it reads as a misclick                                    |
| MOVE_EASE                   | discrete choice             | `power2.inOut` calm · `power3.out` decisive · `back.out(1.2–1.4)` settles onto the button with a tiny recoil (higher reads cartoonish) |
| CLICK_AT                    | `MOVE_DUR + 0–0.3 s`        | zero pause reads as autopilot; >0.3 s reads as hesitation                                                                              |
| PRESS_DUR                   | 0.06–0.12 s (half; yoyo ×2) | short crisp, long mushy; must finish before the next phase needs normal scale                                                          |
| CURSOR / TARGET_PRESS_SCALE | 0.80–0.90 / 0.92–0.97       | cursor compresses MORE than the target — the cursor is the actor, the target the recipient                                             |
| RIPPLE_AT                   | `CLICK_AT + 0–0.08 s`       | simultaneous feels causal; slight delay feels acoustic                                                                                 |
| RIPPLE_DUR                  | 0.5–1.0 s                   | sharp ping vs soft sonar; must complete before anything that needs the ring gone                                                       |
| RIPPLE_SCALE                | 3–6                         | 3 stays near the click site; if the ring would exit the frame before fading, lower it                                                  |
| RIPPLE_STAGGER              | 0.06–0.12 s (or 0)          | below ~0.06 s reads as one thick ring; above ~0.12 s as separate events                                                                |
| RIPPLE_EASE                 | discrete choice             | `power2.out` standard ping · `power3.out` sharper attack · `expo.out` strong distant pulse                                             |
| TARGET_X / TARGET_Y         | layout-derived              | must match the target's visual centroid — a 4 px miss reads as missing the button                                                      |

Reference values: `../../examples/cta-orbit-collapse.html` — 0.5 s move on `back.out(1.3)`, click +0.2 s, press 0.08 s at 0.85/0.95, single ring to 5× over 0.7 s `power2.out`.

## Critical Constraints

- **Move before click** — trigger the click only after the move tween settles; clicking mid-motion reads as unintentional.
- **Rings live in DOM from t=0** at the click-target center with `scale: 0` + `opacity: 0` — never conditionally rendered; `immediateRender: false` on the expand so they hold invisible until the trigger.
- **Ripple from the click point** — the button's visual center, not any element's bounding-box origin.
- **Synchronized depression** — cursor + target depress at the same position with the same duration, and both yoyo back.
- **Cursor above all content** (high z-index) for the whole sequence; `pointer-events: none` on cursor + ripples.

## See also

`orbit-3d-entry` (click as the pivot that collapses orbiters) · `center-outward-expansion` (click triggers an outward burst) · `press-release-spring` (stronger physical feel on the target) · `scale-swap-transition` (the button's post-click state change).
