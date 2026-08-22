# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,".hyperframes")
from fb import *

# ── Frame 11 — recommendations ──────────────────────────────────────────────────
# grid-card-assemble (Adapt): the ranked-vertical-list signature extended with the
# blueprint's optional bar fill, so the ranking is SHOWN rather than asserted. The bars
# fill from the RIGHT — the RTL reversal from the Video direction.
MATCHES = [("mastercard_logo.jpg", "Mastercard Israel", "10/35 חנויות תואמות", "29%", 0.29),
           ("topcash_logo.png", "Isracard TopCash", "31/300 חנויות תואמות", "10%", 0.10)]
m_html = ""
for i, (f, n, s, pct, w) in enumerate(MATCHES):
    m_html += ('<div class="mrow" id="f11-m%d"><span class="m-chip"><img src="assets/%s" alt="" /></span>'
               '<span class="m-tx"><span class="ltr">%s</span><i>%s</i></span>'
               '<span class="m-pct">%s</span>'
               '<span class="m-track"><span class="m-fill" id="f11-f%d"></span></span></div>'
               % (i, f, n, s, pct, i))

body = """
    <div id="f11-bg" class="ground g-cream clip" data-start="0" data-duration="6" data-track-index="0"></div>

    <div id="f11-scene" class="clip stage" data-start="0" data-duration="6" data-track-index="1">
      <div id="f11-anchor" class="anchor num">₪1,284</div>
      <div id="f11-head" class="words f11-head d1 band-a">%(h1)s<span class="mark"><span class="mark-bar" id="f11-bar"></span><span class="mark-ink">כדאי</span></span><span> להצטרף</span></div>
      <div id="f11-rows" class="f11-rows">%(rows)s</div>
      <div id="f11-missed" class="missedcard">
        <span class="ms-lab">חיסכון שפוספס</span>
        <span class="ms-fig fig-card num" id="f11-msfig">0</span>
        <span class="ms-sub">ב-<span class="ltr">FOX - פוקס</span> · ביגוד ואביזרים</span>
      </div>
      <div id="f11-bands" class="bands">
        <span class="band" id="f11-b0">מדויקת</span><span class="band" id="f11-b1">חזקה</span><span class="band" id="f11-b2">דומה</span>
      </div>
    </div>
""" % {"h1": wordspans("לאיזה מועדון"), "rows": m_html}

css = """
        .anchor { position: absolute; top: 0; left: 0; font-family: "Heebo", sans-serif; font-weight: 800;
                  font-size: 112px; font-variant-numeric: tabular-nums; color: var(--payoff);
                  transform-origin: left top; opacity: 0; }
        .f11-head { justify-content: flex-start; }
        .f11-rows { position: absolute; top: 420px; left: 0; right: 0; }
        .mrow { position: relative; background: var(--mint); border-radius: 30px; padding: 28px 30px 40px;
                margin-bottom: 22px; display: flex; align-items: center; gap: 20px; opacity: 0; overflow: hidden; }
        .m-chip { width: 76px; height: 76px; flex: 0 0 76px; background: #fff; border-radius: 18px; overflow: hidden; }
        .m-chip img { width: 100%; height: 100%; object-fit: contain; padding: 8px; box-sizing: border-box; }
        .m-tx { flex: 1; font-family: "Heebo", sans-serif; font-weight: 800; font-size: 36px; color: var(--mint-ink); }
        .m-tx i { display: block; font-style: normal; font-weight: 400; font-size: 26px;
                  color: #4f7d79; margin-top: 4px; }
        .m-pct { background: #fff; border-radius: 100px; padding: 10px 26px; font-family: "Heebo", sans-serif;
                 font-weight: 800; font-size: 34px; color: var(--primary); unicode-bidi: isolate; direction: ltr; }
        .m-track { position: absolute; right: 30px; left: 30px; bottom: 18px; height: 10px;
                   border-radius: 6px; background: #fff; overflow: hidden; }
        .m-fill { position: absolute; inset: 0; background: var(--primary); border-radius: 6px;
                  transform-origin: right center; transform: scaleX(0); }
        .missedcard { position: absolute; top: 880px; left: 0; right: 0; background: #fff;
                      border: 1.5px solid var(--brd); border-radius: 34px; padding: 34px 34px 38px; opacity: 0; }
        .ms-lab { display: block; font-family: "Heebo", sans-serif; font-weight: 600; font-size: 28px;
                  letter-spacing: 0.06em; color: var(--muted); }
        .ms-fig { display: block; margin: 16px 0 14px; font-family: "Heebo", sans-serif; font-weight: 800;
                  font-variant-numeric: tabular-nums; color: var(--ink); line-height: 1.24;
                  transform-origin: right center; }
        .ms-sub { display: block; margin-top: 2px; font-family: "Heebo", sans-serif; font-size: 32px; color: var(--muted); }
        .bands { position: absolute; top: 1300px; left: 0; right: 0; display: flex; gap: 16px; }
        .band { background: var(--mint); color: var(--mint-ink); border-radius: 100px; padding: 16px 34px;
                font-family: "Heebo", sans-serif; font-weight: 700; font-size: 32px; opacity: 0; }
"""

js = """
          /* Scene 1 (0.0–1.2s) — handoff_in: frame 10's ₪1,284 shrinks to ~0.4 and clears to
             the top-right as a persistent anchor (scale-swap-transition). */
          tl.fromTo(el("f11-anchor"), { opacity: 1, scale: 1 },
                    { opacity: 0.5, scale: 0.4, duration: 0.66, ease: "power3.inOut" }, 0);
          words("#f11-head > span, #f11-head > .mark", 0.18, 0.085, 0.46, 32);
          sweep(el("f11-bar"), 0.72, 0.4);

          /* Scene 2 (1.2–3.0s) — the ranked rows, one per bar, each bar filling from the RIGHT. */
          for (var i = 0; i < 2; i++) {
            var at = 1.22 + i * 0.78;
            tl.fromTo(el("f11-m" + i), { opacity: 0, x: 90 },
                      { opacity: 1, x: 0, duration: 0.52, ease: "power3.out" }, at);
            fill(el("f11-f" + i), at + 0.26, 0.86, i === 0 ? 0.29 : 0.10);
          }

          /* Scene 3 (3.0–4.4s) — the missed-savings card DETACHES upward out of the list and
             scales up. The figure counts in `text`, NOT gold: this is a loss, not a payoff. */
          tl.fromTo(el("f11-missed"), { opacity: 0, scale: 0.8, y: 90 },
                    { opacity: 1, scale: 1, y: 0, duration: 0.7, ease: "power3.out" }, 3.02);
          countTo(el("f11-msfig"), 340, 3.26, 0.9, 0.62, function (v) { return "\\u20AA" + v.toLocaleString("en-US"); });

          /* Scene 4 (4.4–6.0s) — three certainty chips hard-cut right→left. */
          hardcut(el("f11-b0"), 4.42); hardcut(el("f11-b1"), 4.64); hardcut(el("f11-b2"), 4.86);
          jitter(el("f11-rows"), 5.10, 0.86);
"""
print(emit("11-recommendations", body, css, js))


# ── Frame 12 — notifications ────────────────────────────────────────────────────
# agent-progress-theater (Adapt): keep the machine-finishes-and-the-receipt-arrives
# signature, compressed to its second half. The working state already happened —
# off-screen and unattended — which is precisely the claim. So the frame opens on arrival.
DEVICE_X, DEVICE_Y = 290, 498
body = """
    <div id="f12-bg" class="ground g-dark clip" data-start="0" data-duration="5" data-track-index="0"></div>

    <div id="f12-scene" class="clip on-dark" data-start="0" data-duration="5" data-track-index="1">
      <div class="device" id="f12-dev" style="left:%(dx)dpx;top:%(dy)dpx;">
        <div class="device-screen"><div class="island"></div><div class="dim-screen"><div class="rest-head"></div><div class="rest-card"></div><div class="rest-row"></div><div class="rest-row"></div><div class="rest-nav"></div></div></div>
        <div class="device-rim"></div>
      </div>
      <div id="f12-toast" class="toast">
        <img class="toast-mark" src="assets/logo-without-name.svg" alt="" />
        <span class="toast-tx">הניתוח מוכן<i>הרגע</i></span>
      </div>
      <div id="f12-badges" class="badges">
        <span class="badge" id="f12-g0">ניתוח</span><span class="badge" id="f12-g1">מועדונים</span>
        <span class="badge" id="f12-g2">דיל</span><span class="badge" id="f12-g3">מערכת</span>
      </div>
      <div id="f12-head" class="words f12-head d1 band-b">%(h)s<span class="mark"><span class="mark-bar" id="f12-bar"></span><span class="mark-ink">לבד.</span></span></div>
      <div id="f12-foot" class="f12-foot sup">בלי לרענן. בלי לחפש.</div>
    </div>
""" % {"dx": DEVICE_X, "dy": DEVICE_Y, "h": wordspans("מגיע אליכם ")}

css = """
        .dim-screen { position: absolute; inset: 0; background: #e7eef1; padding: 78px 22px 0; box-sizing: border-box; }
        .rest-head { height: 54px; background: #d3dee4; border-radius: 14px; }
        .rest-card { height: 210px; margin-top: 18px; background: #c6d4dc; border-radius: 26px; }
        .rest-row { height: 96px; margin-top: 14px; background: #d3dee4; border-radius: 20px; }
        .rest-nav { position: absolute; left: 22px; right: 22px; bottom: 26px; height: 74px;
                    background: #b8c8d2; border-radius: 100px; }
        .toast { position: absolute; left: 100px; right: 100px; top: 660px; display: flex; align-items: center;
                 gap: 20px; background: #fff; border-radius: 32px; padding: 30px 32px; opacity: 0;
                 box-shadow: 0 30px 70px rgba(6,12,20,0.6); }
        .toast-mark { width: 62px; height: 62px; flex: 0 0 62px; }
        .toast-tx { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 42px; color: var(--ink); }
        .toast-tx i { display: block; font-style: normal; font-weight: 400; font-size: 26px;
                      color: var(--muted); margin-top: 4px; }
        .badges { position: absolute; left: 100px; right: 100px; top: 880px; display: flex;
                  flex-wrap: wrap; gap: 14px; }
        .badge { background: var(--dark-surface); border: 1.5px solid rgba(241,246,248,0.16);
                 border-radius: 100px; padding: 14px 30px; opacity: 0;
                 font-family: "Heebo", sans-serif; font-weight: 600; font-size: 30px; color: var(--dark-ink); }
        .f12-head { left: 72px; right: 72px; justify-content: flex-start; }
        .f12-foot { position: absolute; top: 490px; left: 72px; right: 72px; opacity: 0; }
"""

js = """
          /* Scene 1 (0.0–1.0s) — the carrier is back at rest, screen dim, nothing happening.
             One beat of genuine stillness so the interruption reads AS an interruption. */
          tl.fromTo(el("f12-dev"), { opacity: 0, y: 40 },
                    { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0);

          /* Scene 2 (1.0–2.2s) — the toast drops from the top edge and settles on a long tail.
             It is the only lit thing in frame. */
          tl.fromTo(el("f12-toast"), { opacity: 0, y: -190, scale: 0.94 },
                    { opacity: 1, y: 0, scale: 1, duration: 0.72, ease: "power3.out" }, 1.02);

          /* Scene 3 (2.2–3.6s) — four badges cascade right→left, one per half-bar. */
          for (var i = 0; i < 4; i++) { pop(el("f12-g" + i), 2.22 + i * 0.2, 0.4, 0.86); }

          /* Scene 4 (3.6–5.0s) */
          words("#f12-head > span, #f12-head > .mark", 0.12, 0.09, 0.46, 32);
          sweep(el("f12-bar"), 0.62, 0.4);
          rise(el("f12-foot"), 3.70, 0.44, 26);
"""
print(emit("12-notifications", body, css, js))
