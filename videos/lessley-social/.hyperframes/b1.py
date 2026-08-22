# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,".hyperframes")
from fb import *

# ── Frame 1 — the hook ──────────────────────────────────────────────────────────
# dataviz-countup (Adapt): the cold-open-on-one-statistic signature, with the
# blueprint's icon burst + camera push dropped (no room in vertical, and a push would
# fight the count). Escalation comes from the counter's own value-scaled growth.
body = """
    <div id="f1-bg" class="ground g-cream clip" data-start="0" data-duration="6" data-track-index="0"></div>

    <div id="f1-scene" class="clip stage" data-start="0" data-duration="6" data-track-index="1">
      <div id="f1-figwrap" class="figwrap">
        <span id="f1-fig" class="fig fig-hero gold num">0</span>
      </div>
      <div id="f1-sub" class="words sub">%(sub)s</div>
      <div id="f1-q" class="words q d1">%(q1)s<span class="mark"><span class="mark-bar" id="f1-bar"></span><span class="mark-ink">קיבלתם?</span></span></div>
      <img id="f1-logo" class="mark-logo" src="assets/logo-without-name.svg" alt="Lessley" />
    </div>
""" % {"sub": wordspans("כבר היו שלכם"), "q1": wordspans("כמה מזה באמת ")}

css = """
        .figwrap { position: absolute; top: 260px; left: 0; right: 0; text-align: center; }
        
        .gold { color: var(--payoff-ink); }
        .sub { position: absolute; top: 600px; left: 0; right: 0; justify-content: center;
               font-family: "Heebo", sans-serif; font-weight: 600; font-size: 44px; color: var(--muted); }
        .q { position: absolute; top: 820px; left: 0; right: 0; justify-content: center; }
        .mark-logo { position: absolute; bottom: 40px; left: 0; width: 118px; height: 118px; opacity: 0; }
"""

js = """
          /* Scene 1 (0.0–2.2s) — the figure alone. Nothing else exists yet. */
          var fig = el("f1-fig");
          countTo(fig, 1284, 0.15, 1.9, 0.52, function (v) { return "\\u20AA" + v.toLocaleString("en-US"); });
          tl.set(fig, { opacity: 1 }, 0);

          /* Scene 2 (2.2–3.6s) — the counter locks; the line arrives per-word, right→left. */
          words("#f1-sub > span", 1.90, 0.10, 0.46, 28);

          /* Scene 3 (3.6–5.2s) — the question, then the marker sweep on its payoff word. */
          words("#f1-q > span, #f1-q > .mark", 2.95, 0.085, 0.48, 34);
          sweep(el("f1-bar"), 3.72, 0.44);

          /* Scene 4 (5.2–6.0s) — held read. Mark fades up; subtle jitter only. */
          fade(el("f1-logo"), 4.70, 0.5, 0.5);
          jitter(el("f1-figwrap"), 4.60, 1.3);
"""
print(emit("01-hook", body, css, js))


# ── Frame 2 — the pain ──────────────────────────────────────────────────────────
# overwhelm-surround (Adapt): the close-in-from-all-sides signature. The avatar morph
# is dropped (no character in this film); the ten club chips are the density markers and
# each carries a ₪0 stamp so the crowding means something.
CHIPS = [
    ("mastercard_logo.jpg", 92, 150, 210),
    ("topcash_logo.png", 640, 96, 176),
    ("hever_giftcard_logo.jpg", 330, 372, 186),
    ("paisplus_logo.jpg", 726, 430, 168),
    ("hot_logo.png", 108, 610, 172),
    ("hever_teamim_logo.jpg", 560, 700, 190),
    ("paisplus_food_chains_logo.png", 830, 806, 160),
    ("swish_logo.png", 236, 900, 176),
    ("paisplus_networks_logo.jpg", 610, 1024, 168),
]
chips_html = []
for i, (f, x, y, s) in enumerate(CHIPS):
    chips_html.append(
        '<div class="chipwrap" id="f2-c%d" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;">'
        '<div class="chip" style="width:100%%;height:100%%;"><img src="assets/%s" alt="" /></div>'
        '<span class="zero" id="f2-z%d">₪0</span></div>' % (i, x, y, s, s, f, i))
# Behatsdaa ships no logo file — a type-only chip in the identical shape keeps the field at ten.
chips_html.append(
    '<div class="chipwrap" id="f2-c9" style="left:300px;top:1180px;width:200px;height:172px;">'
    '<div class="chip name-chip" style="width:100%;height:100%;">בהצדעה</div>'
    '<span class="zero" id="f2-z9">₪0</span></div>')

body = """
    <div id="f2-bg" class="ground g-dark clip" data-start="0" data-duration="5" data-track-index="0"></div>

    <div id="f2-scene" class="clip stage on-dark" data-start="0" data-duration="5" data-track-index="1">
      <div id="f2-field" data-layout-allow-overlap>%(chips)s</div>
      <div id="f2-l1" class="words line1 d1 band-b">%(l1)s</div>
      <div id="f2-l2" class="line2 impact">אפס מעקב.</div>
    </div>
""" % {"chips": "".join(chips_html), "l1": wordspans("עשרה מועדונים.")}

css = """
        #f2-field { position: absolute; inset: 0; z-index: 1; }
        .chipwrap { position: absolute; }
        .name-chip { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 34px;
                     color: var(--dark); background: #fff; }
        .zero { position: absolute; bottom: -14px; right: -10px; background: var(--dark-surface);
                color: var(--dark-muted); border: 1.5px solid rgba(241,246,248,0.14);
                border-radius: 100px; padding: 6px 18px; font-family: "Heebo", sans-serif;
                font-weight: 800; font-size: 26px; unicode-bidi: isolate; direction: ltr; }
        .line1 { justify-content: center; z-index: 6; text-shadow: 0 6px 26px rgba(12,20,28,0.98),
                 0 2px 10px rgba(12,20,28,0.95); }
        .line2 { position: absolute; top: 470px; left: 0; right: 0; text-align: center; z-index: 6;
                 color: var(--primary); text-shadow: 0 6px 30px rgba(12,20,28,0.9); }
"""

js = """
          /* Scene 1 (0.0–1.4s) — three chips arrive from the right edge, right→left stagger. */
          var order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
          var cx = 468, cy = 940;   /* convergence sits BELOW the type band, not through it */
          for (var i = 0; i < order.length; i++) {
            var c = el("f2-c" + order[i]);
            if (!c) continue;
            var at = (i < 3) ? (0.10 + i * 0.22) : (1.42 + (i - 3) * 0.17);
            tl.fromTo(c, { opacity: 0, x: 300 + i * 26, y: -40 + (i % 3) * 34, scale: 0.86 },
                         { opacity: 1, x: 0, y: 0, scale: 1, duration: 0.62, ease: "power3.out" }, at);
            /* depth: chips further down the stagger sit back, slightly blurred */
            if (i % 3 === 2) tl.set(c, { filter: "blur(3px)", opacity: 0.82 }, 0);
          }

          /* Scene 2 (1.4–2.8s) — the line reads THROUGH the crowd as it keeps arriving. */
          words("#f2-l1 > span", 1.46, 0.10, 0.46, 30);

          /* Scene 3 (2.8–4.2s) — every ₪0 stamp flips on, then the field closes IN on center
             (the inverse of center-outward-expansion). */
          for (var z = 0; z < 10; z++) { pop(el("f2-z" + z), 2.82 + z * 0.045, 0.3, 0.7); }
          for (var k = 0; k < order.length; k++) {
            var ch = el("f2-c" + order[k]);
            if (!ch) continue;
            var r = ch.getBoundingClientRect ? null : null;
            var lx = parseFloat(ch.style.left) + parseFloat(ch.style.width) / 2;
            var ly = parseFloat(ch.style.top) + parseFloat(ch.style.height) / 2;
            tl.to(ch, { x: (cx - lx) * 0.40, y: (cy - ly) * 0.40, duration: 1.05,
                        ease: "power2.inOut" }, 3.16 + (k % 4) * 0.03);
          }

          /* Scene 4 (4.2–5.0s) — one hard word slams dead-center on the peak of the crowding. */
          tl.fromTo(el("f2-l2"), { opacity: 0, scale: 1.24 },
                    { opacity: 1, scale: 1, duration: 0.34, ease: "power4.out" }, 4.20);
          tl.to(el("f2-l1"), { opacity: 0.28, duration: 0.3, ease: "power2.out" }, 4.20);
"""
print(emit("02-problem", body, css, js))
