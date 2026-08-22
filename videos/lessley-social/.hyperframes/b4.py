# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,".hyperframes")
from fb import *

# ── Frame 7 — the payoff ────────────────────────────────────────────────────────
# dataviz-countup (Adapt): keep the land-on-one-hero-metric signature. The count
# DESCENDS (the value falling is the good news) and the blueprint's camera push-through
# is replaced by a full beat of stillness before the payoff — the climax earns it.
body = """
    <div id="f7-bg" class="ground g-cream clip" data-start="0" data-duration="7" data-track-index="0"></div>

    <div id="f7-scene" class="clip stage" data-start="0" data-duration="7" data-track-index="1">
      <div id="f7-glow" class="glow"></div>
      <div id="f7-card" class="card stackcard">
        <div class="stack-band">
          <span class="band-trophy">%(tro)s</span>
          <span class="band-tx">השילוב הטוב ביותר<i>FOX - פוקס · דיל אחד הופעל</i></span>
          <span class="band-chip"><img src="assets/hever_giftcard_logo.jpg" alt="" /></span>
        </div>
        <div class="stack-body">
          <div class="old-wrap"><span class="oldfig num" id="f7-old">₪1,000</span><span class="strike" id="f7-strike"></span></div>
          <div class="pay-lab" id="f7-lab">אתם משלמים</div>
          <div class="payfig fig-payoff num" id="f7-pay">₪1,000</div>
        </div>
      </div>
      <div id="f7-pill" class="pill pill-gold savepill">חיסכון ₪300 (30%%)</div>
      <div id="f7-foot" class="f7-foot sup">לא הערכה — דיל אמיתי, זמין עכשיו.</div>
    </div>
""" % {"tro": '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
              '<path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" stroke="#fff" stroke-width="1.7" stroke-linejoin="round"/>'
              '<path d="M7 5H4.5v1.5A3.5 3.5 0 0 0 8 10M17 5h2.5v1.5A3.5 3.5 0 0 1 16 10" stroke="#fff" stroke-width="1.7"/>'
              '<path d="M12 14v4m-3 2h6" stroke="#fff" stroke-width="1.7" stroke-linecap="round"/></svg>'}

css = """
        .glow { position: absolute; left: 50%; top: 470px; width: 900px; height: 900px;
                margin-left: -450px; margin-top: -450px; border-radius: 50%;
                background: radial-gradient(circle, rgba(241,164,70,0.30) 0%, rgba(241,164,70,0) 66%);
                opacity: 0; }
        .stackcard { position: absolute; top: 90px; left: 0; right: 0; overflow: hidden; opacity: 0; }
        .stack-band { display: flex; align-items: center; gap: 18px; background: var(--primary);
                      padding: 26px 30px; }
        .band-trophy { width: 46px; height: 46px; flex: 0 0 46px; background: rgba(255,255,255,0.18);
                       border-radius: 50%; padding: 9px; box-sizing: border-box; }
        .band-trophy svg { width: 100%; height: 100%; }
        .band-tx { flex: 1; font-family: "Heebo", sans-serif; font-weight: 800; font-size: 38px; color: #fff; }
        .band-tx i { display: block; font-style: normal; font-weight: 400; font-size: 24px;
                     color: rgba(255,255,255,0.82); margin-top: 4px; }
        .band-chip { width: 62px; height: 62px; background: #fff; border-radius: 16px; overflow: hidden; }
        .band-chip img { width: 100%; height: 100%; object-fit: contain; padding: 7px; box-sizing: border-box; }
        .stack-body { padding: 44px 34px 52px; text-align: center; }
        .old-wrap { position: relative; display: inline-block; }
        .oldfig { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 64px;
                  font-variant-numeric: tabular-nums; color: var(--muted); }
        .strike { position: absolute; right: -6px; left: -6px; top: 52%; height: 6px; border-radius: 3px;
                  background: var(--muted); transform-origin: right center; transform: scaleX(0); }
        .pay-lab { margin-top: 34px; margin-bottom: 18px; font-family: "Heebo", sans-serif; font-weight: 600; font-size: 32px;
                   color: var(--muted); opacity: 0; }
        .payfig { display: block; font-family: "Heebo", sans-serif; font-weight: 800;
                  font-variant-numeric: tabular-nums; color: var(--primary); line-height: 1.24;
                  transform-origin: center center; }
        .savepill { position: absolute; top: 1000px; left: 50%; transform: translateX(-50%);
                    font-size: 44px; font-weight: 800; padding: 24px 52px; opacity: 0; }
        .f7-foot { position: absolute; top: 1150px; left: 0; right: 0; text-align: center; opacity: 0; }
"""

js = """
          /* Scene 1 (0.0–1.4s) — handoff_in: ₪1,000 arrives at the exact centre it held in
             frame 6, no jump. The winning-stack card assembles under it. */
          tl.fromTo(el("f7-card"), { opacity: 0, y: 60, scale: 0.96 },
                    { opacity: 1, y: 0, scale: 1, duration: 0.78, ease: "power3.out" }, 0.05);

          /* Scene 2 (1.4–2.6s) — the strike-through is DRAWN right→left, never faded on. */
          sweep(el("f7-strike"), 1.42, 0.46);

          /* Scene 3 (2.6–4.2s) — the hero count. It DESCENDS 1,000 → 700; the struck old
             figure stays visible above it, because the contrast IS the argument. */
          rise(el("f7-lab"), 2.60, 0.4, 20);
          var pay = el("f7-pay");
          countFrom(pay, 1000, 700, 2.72, 1.25, function (v) { return "\\u20AA" + v.toLocaleString("en-US"); });
          tl.fromTo(pay, { scale: 0.78 }, { scale: 1, duration: 1.25, ease: "power3.out" }, 2.72);

          /* Scene 4 (4.2–5.2s) — HELD. One full beat, nothing moving, not even jitter.
             The silence is what makes the next beat land. */

          /* Scene 5 (5.2–7.0s) — the gold pill springs in (smooth settle, no overshoot —
             it is data punctuation, not decoration) and the glow blooms once behind it. */
          pop(el("f7-pill"), 5.20, 0.54, 0.86);
          tl.fromTo(el("f7-glow"), { opacity: 0, scale: 0.82 },
                    { opacity: 1, scale: 1, duration: 0.9, ease: "power2.out" }, 5.16);
          rise(el("f7-foot"), 5.72, 0.46, 24);
          jitter(el("f7-card"), 6.30, 0.66);
"""
print(emit("07-payoff", body, css, js))


# ── Frame 8 — how it stacks ─────────────────────────────────────────────────────
# grid-card-assemble (Reproduce): a vertical list that accumulates row by row and holds.
# The disclosure IS an accumulating list, so the blueprint needs no adaptation.
ROWS = [("ההנחה חלה על", "₪1,000", None), ("משלמים עליו", "₪700", None),
        ("נשאר לתשלום", "₪700", "₪1,000")]
rows_html = ""
for i, (lab, val, was) in enumerate(ROWS):
    old = ('<span class="rw-was num">%s</span>' % was) if was else ""
    rows_html += ('<div class="steprow" id="f8-r%d"><span class="rw-lab">%s</span>'
                  '<span class="rw-vals">%s<span class="rw-val num">%s</span></span></div>' % (i, lab, old, val))
    if i < len(ROWS) - 1:
        rows_html += ('<svg class="chev" id="f8-v%d" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
                      '<path class="ck" d="M6 9l6 6 6-6" stroke="#397c7f" stroke-width="2.6" '
                      'stroke-linecap="round" stroke-linejoin="round"/></svg>' % i)

body = """
    <div id="f8-bg" class="ground g-cream clip" data-start="0" data-duration="5" data-track-index="0"></div>

    <div id="f8-scene" class="clip stage" data-start="0" data-duration="5" data-track-index="1">
      <div id="f8-card" class="card f8-head-card">
        <div class="stack-band-s">
          <span class="band-chip-s"><img src="assets/hever_giftcard_logo.jpg" alt="" /></span>
          <span class="band-tx-s">השילוב הטוב ביותר<i>Hever · כרטיס מתנה · 30%% הנחה</i></span>
        </div>
      </div>
      <div id="f8-lab" class="f8-lab d1 band-b">איך זה מצטבר</div>
      <div id="f8-rows" class="f8-rows">%(rows)s</div>
      <div id="f8-foot" class="f8-foot sup">כל שקל מוסבר צעד-צעד.</div>
    </div>
""" % {"rows": rows_html}

css = """
        .f8-head-card { position: absolute; top: 650px; left: 0; right: 0; overflow: hidden; }
        .stack-band-s { display: flex; align-items: center; gap: 16px; background: var(--primary); padding: 22px 28px; }
        .band-chip-s { width: 56px; height: 56px; background: #fff; border-radius: 14px; overflow: hidden; flex: 0 0 56px; }
        .band-chip-s img { width: 100%; height: 100%; object-fit: contain; padding: 6px; box-sizing: border-box; }
        .band-tx-s { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 34px; color: #fff; }
        .band-tx-s i { display: block; font-style: normal; font-weight: 400; font-size: 22px;
                       color: rgba(255,255,255,0.82); margin-top: 3px; }
        .f8-lab { opacity: 0; }
        .f8-rows { position: absolute; top: 640px; left: 0; right: 0; }
        .steprow { display: flex; align-items: center; justify-content: space-between; opacity: 0;
                   background: var(--mint); border-radius: 26px; padding: 30px 34px; }
        .rw-lab { font-family: "Heebo", sans-serif; font-weight: 600; font-size: 40px; color: var(--mint-ink); }
        .rw-vals { display: flex; align-items: baseline; gap: 18px; }
        .rw-was { font-family: "Heebo", sans-serif; font-weight: 600; font-size: 32px; color: #7fa6a3;
                  text-decoration: line-through; font-variant-numeric: tabular-nums; }
        .rw-val { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 48px;
                  color: var(--mint-ink); font-variant-numeric: tabular-nums; }
        .chev { display: block; width: 46px; height: 46px; margin: 10px auto; }
        .f8-foot { position: absolute; top: 1230px; left: 0; right: 0; opacity: 0; }
"""

js = """
          /* Scene 1 (0.0–1.0s) — the winning-stack card continues from frame 7, then slides
             up on a nudge-curve (slow → fast → slow) to open room beneath it. */
          tl.set(el("f8-card"), { y: 180 }, 0);
          tl.to(el("f8-card"), { y: 60, duration: 0.24, ease: "power1.in" }, 0.05);
          tl.to(el("f8-card"), { y: -100, duration: 0.42, ease: "none" }, 0.29);
          tl.to(el("f8-card"), { y: -180, duration: 0.3, ease: "power2.out" }, 0.71);
          rise(el("f8-lab"), 0.52, 0.44, 26);

          /* Scene 2 (1.0–3.4s) — rows cascade right→left, one per beat, chevrons drawing
             between consecutive steps. */
          for (var i = 0; i < 3; i++) {
            var at = 1.02 + i * 0.62;
            tl.fromTo(el("f8-r" + i), { opacity: 0, x: 80 },
                      { opacity: 1, x: 0, duration: 0.5, ease: "power3.out" }, at);
            if (i < 2) draw(ROOT.querySelector("#f8-v" + i + " .ck"), at + 0.4, 0.26);
          }

          /* Scene 3 (3.4–4.4s) */
          rise(el("f8-foot"), 3.42, 0.44, 24);

          /* Scene 4 (4.4–5.0s) — held: the whole arithmetic visible at once, which is the point. */
          jitter(el("f8-rows"), 4.44, 0.54);
"""
print(emit("08-how-it-stacks", body, css, js))
