# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,".hyperframes")
from fb import *

CK = CHECK_SVG % "#397c7f"

# ── Frame 9 — the deal finder (cascade opener) ──────────────────────────────────
# cursor-ui-demo (Adapt): keep the cursor-drives-real-state-changes-onto-the-action-
# control signature. Adapted for the cascade's doubled pace — the cursor does ONE thing
# (the copy press); the filtering happens as a card cascade, not a click-through.
CARDS = [("hot_logo.png", "HOT Israel", "15% הנחה", 0), ("swish_logo.png", "Swish", "10% הנחה", 1),
         ("topcash_logo.png", "TopCash", "5% חזרה", 2)]
cards_html = "".join(
    '<div class="dealcard" id="f9-d%d"><span class="dc-chip"><img src="assets/%s" alt="" /></span>'
    '<span class="dc-tx">%s<i>%s</i></span></div>' % (i, f, n, d) for f, n, d, i in CARDS)

body = """
    <div id="f9-bg" class="ground g-dark clip" data-start="0" data-duration="5" data-track-index="0"></div>

    <div id="f9-scene" class="clip stage on-dark" data-start="0" data-duration="5" data-track-index="1">
      <div id="f9-head" class="words f9-head d1 band-a">%(h)s</div>
      <div id="f9-chips" class="f9-chips">
        <span class="fchip" id="f9-fc0">חנות</span><span class="fchip" id="f9-fc1">קטגוריה</span><span class="fchip" id="f9-fc2">חיפוש חופשי</span>
      </div>
      <div id="f9-cards" class="f9-cards">%(cards)s</div>
      <div id="f9-btn" class="copybtn"><span id="f9-b1">העתקה</span><span id="f9-b2" class="swapped2">הועתק %(ck)s</span></div>
      <div class="cursor" id="f9-cur">%(cur)s</div>
      <div id="f9-foot" class="f9-foot d2">קוד קופון <span class="mark"><span class="mark-bar" id="f9-bar"></span><span class="mark-ink">בלחיצה.</span></span></div>
    </div>
""" % {"h": wordspans("כל הדילים שלכם במקום אחד"), "cards": cards_html, "cur": CURSOR_SVG, "ck": CK}

css = """
        .f9-head { justify-content: flex-start; }
        .f9-chips { position: absolute; top: 330px; left: 0; right: 0; display: flex; gap: 16px; }
        .fchip { background: var(--dark-surface); border: 1.5px solid rgba(241,246,248,0.16);
                 border-radius: 100px; padding: 16px 32px; opacity: 0;
                 font-family: "Heebo", sans-serif; font-weight: 600; font-size: 30px; color: var(--dark-ink); }
        .f9-cards { position: absolute; top: 490px; left: 0; right: 0; }
        .dealcard { display: flex; align-items: center; gap: 26px; background: #fff; border-radius: 34px;
                    padding: 40px 34px; margin-bottom: 26px; opacity: 0; }
        .dc-chip { width: 104px; height: 104px; flex: 0 0 104px; border-radius: 18px; overflow: hidden;
                   border: 1px solid #dde5e9; }
        .dc-chip img { width: 100%; height: 100%; object-fit: contain; padding: 8px; box-sizing: border-box; }
        .dc-tx { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 48px; color: var(--ink); }
        .dc-tx i { display: block; font-style: normal; font-weight: 600; font-size: 30px;
                   color: var(--primary); margin-top: 4px; }
        .copybtn { position: absolute; top: 980px; left: 0; right: 0; background: var(--primary);
                   color: #fff; border-radius: 100px; text-align: center; padding: 26px 0; opacity: 0;
                   font-family: "Heebo", sans-serif; font-weight: 700; font-size: 40px; }
        .copybtn span { display: inline-flex; align-items: center; gap: 14px; justify-content: center; }
        .copybtn .swapped2 { position: absolute; inset: 0; opacity: 0; }
        .copybtn svg { width: 42px; height: 42px; }
        .copybtn svg path { stroke: #fff; }
        .f9-foot { position: absolute; top: 1170px; left: 0; right: 0; opacity: 0; }
        #f9-cur { left: 700px; top: 1500px; opacity: 0; }
"""

js = """
          /* Scene 1 (0.0–1.2s) — a section boundary: the ground change announces it.
             Cards are already streaming in behind the headline. */
          words("#f9-head > span", 0.06, 0.075, 0.44, 30);
          for (var i = 0; i < 3; i++) {
            tl.fromTo(el("f9-d" + i), { opacity: 0, x: 110 },
                      { opacity: 1, x: 0, duration: 0.5, ease: "power3.out" }, 0.42 + i * 0.13);
          }

          /* Scene 2 (1.2–2.4s) — filter chips hard-cut on right→left; on the third the stack
             FILTERS DOWN: non-matching cards fall away with a velocity smear. */
          hardcut(el("f9-fc0"), 1.22); hardcut(el("f9-fc1"), 1.44); hardcut(el("f9-fc2"), 1.66);
          for (var k = 1; k < 3; k++) {
            tl.to(el("f9-d" + k), { x: -300, opacity: 0, filter: "blur(10px)", scaleY: 0.92,
                                    duration: 0.42, ease: "power2.in" }, 1.72 + k * 0.06);
          }
          tl.to(el("f9-d0"), { scale: 1.14, y: 70, duration: 0.6, ease: "power3.out" }, 1.80);

          /* Scene 3 (2.4–3.8s) — the one cursor beat: press, spring back, label hard-cuts,
             check self-draws. */
          fade(el("f9-btn"), 2.34, 0.34);
          tl.set(el("f9-cur"), { opacity: 1 }, 2.40);
          tl.fromTo(el("f9-cur"), { x: 0, y: 0 }, { x: -220, y: -640, duration: 0.6, ease: "power2.inOut" }, 2.42);
          tl.to(el("f9-cur"), { scale: 0.88, duration: 0.1, ease: "power2.in" }, 3.04);
          tl.to(el("f9-cur"), { scale: 1, duration: 0.28, ease: "power3.out" }, 3.14);
          tl.to(el("f9-btn"), { scale: 0.965, duration: 0.1, ease: "power2.in" }, 3.04);
          tl.to(el("f9-btn"), { scale: 1, duration: 0.34, ease: "power3.out" }, 3.14);
          hardhide(el("f9-b1"), 3.18); hardcut(el("f9-b2"), 3.18);
          draw(ROOT.querySelector("#f9-b2 .ck"), 3.24, 0.3);
          tl.to(el("f9-cur"), { opacity: 0, duration: 0.28, ease: "power2.out" }, 3.42);

          /* Scene 4 (3.8–5.0s) */
          rise(el("f9-foot"), 3.80, 0.46, 30);
          sweep(el("f9-bar"), 4.16, 0.4);
"""
print(emit("09-deal-finder", body, css, js))


# ── Frame 10 — insights ─────────────────────────────────────────────────────────
# grid-card-assemble (Adapt): keep the self-assembling-array-that-enumerates-breadth
# signature, but the array FANS as a five-slide carousel — the real shape of the screen,
# and a fan reads at vertical scale where a 5-up grid does not.
SLIDES = [("סקירה כללית", -2), ("קטגוריות", -1), ("חנויות מובילות", 0), ("עסקאות", 1), ("חשבונות", 2)]
slides_html = "".join(
    '<div class="slide" id="f10-s%d" style="z-index:%d;"><span class="sl-dot"></span>'
    '<span class="sl-tx">%s</span></div>' % (i, 10 - abs(o), t) for i, (t, o) in enumerate(SLIDES))

body = """
    <div id="f10-bg" class="ground g-cream clip" data-start="0" data-duration="6" data-track-index="0"></div>

    <div id="f10-scene" class="clip stage" data-start="0" data-duration="6" data-track-index="1">
      <div id="f10-head" class="words f10-head d1 band-b">%(h)s</div>
      <div id="f10-hero" class="herocard">
        <span class="hc-lab">נחסך עם LESSLEY</span>
        <span class="hc-fig fig-card num" id="f10-fig">0</span>
        <span class="hc-sub">30 הימים האחרונים · 10 מועדונים</span>
      </div>
      <div id="f10-fan" class="fan">%(slides)s</div>
    </div>
""" % {"h": wordspans("הכסף שלכם, מפוענח"), "slides": slides_html}

css = """
        .f10-head { justify-content: flex-start; }
        .herocard { position: absolute; top: 470px; left: 0; right: 0; background: var(--dark);
                    border-radius: 38px; padding: 40px 38px; opacity: 0; text-align: right; }
        .hc-lab { display: block; font-family: "Heebo", sans-serif; font-weight: 600; font-size: 26px;
                  letter-spacing: 0.1em; color: var(--dark-muted); }
        .hc-fig { display: block; margin: 14px 0 12px; font-family: "Heebo", sans-serif; font-weight: 800;
                  font-variant-numeric: tabular-nums; color: #fff; line-height: 1.22;
                  transform-origin: right center; }
        .hc-sub { display: block; margin-top: 4px; font-family: "Heebo", sans-serif; font-size: 28px;
                  color: var(--dark-muted); }
        .fan { position: absolute; top: 880px; left: 0; right: 0; height: 580px; }
        .slide { position: absolute; left: 50%; top: 0; width: 274px; margin-left: -137px; height: 268px;
                 background: #fff; border: 1.5px solid var(--brd); border-radius: 34px; opacity: 0;
                 padding: 26px 24px; box-sizing: border-box; box-shadow: 0 18px 46px rgba(24,39,52,0.10); }
        .sl-dot { display: block; width: 56px; height: 56px; border-radius: 16px; background: var(--mint); }
        .sl-tx { display: block; margin-top: 26px; font-family: "Heebo", sans-serif; font-weight: 800;
                 font-size: 40px; color: var(--ink); line-height: 1.2; }
"""

js = """
          /* Scene 1 (0.0–1.2s) */
          words("#f10-head > span", 0.06, 0.09, 0.46, 32);

          /* Scene 2 (1.2–2.8s) — frame 1's figure returns, now EXPLAINED rather than
             asserted. The count is the callback. */
          tl.fromTo(el("f10-hero"), { opacity: 0, y: 46 },
                    { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 1.20);
          countTo(el("f10-fig"), 1284, 1.44, 1.2, 0.6, function (v) { return "\\u20AA" + v.toLocaleString("en-US"); });

          /* Scene 3 (2.8–5.0s) — center-outward-expansion: the five slides start clustered
             at centre and expand outward into an overlapping fan, right→left, one per
             half-bar. Layered depth: the outer cards sit back. */
          var SP = [[-296, 0, 1.0, 0], [0, 0, 1.0, 0], [296, 0, 1.0, 0], [-150, 300, 1.0, 0], [150, 300, 1.0, 0]];
          for (var i = 0; i < 5; i++) {
            var s = el("f10-s" + i);
            tl.fromTo(s, { opacity: 0, x: 0, y: 0, scale: 0.7, rotation: 0 },
                      { opacity: 1, x: SP[i][0], y: SP[i][1], scale: SP[i][2], rotation: SP[i][3],
                        duration: 0.72, ease: "power3.out" }, 2.82 + i * 0.16);
            
          }

          /* Scene 4 (5.0–6.0s) — the fan locks. Held read; jitter only. */
          jitter(el("f10-fan"), 5.02, 0.9);
"""
print(emit("10-insights", body, css, js))
