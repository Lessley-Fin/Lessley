# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,".hyperframes")
from fb import *

DEVICE_X, DEVICE_Y = 290, 498       # left/top so the device centres at x540, y1040
def device(fid, screen_html, extra=""):
    return """
      <div class="device" id="%s-dev" data-layout-allow-overlap style="left:%dpx;top:%dpx;%s">
        <div class="device-screen">
          <div class="island"></div>
          %s
        </div>
        <div class="device-rim"></div>
      </div>""" % (fid, DEVICE_X, DEVICE_Y, extra, screen_html)

HEADER = """
          <div class="app-head">
            <img class="app-mark" src="assets/logo-without-name.svg" alt="" />
            <div class="app-name">Lessley<span>טייס אוטומטי פיננסי</span></div>
          </div>"""

APP_CSS = """
        .app-head { display: flex; align-items: center; gap: 14px; padding: 62px 24px 16px;
                    background: #fff; border-bottom: 1px solid #dde5e9; }
        .app-mark { width: 46px; height: 46px; }
        .app-name { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 24px;
                    color: var(--ink); line-height: 1.1; }
        .app-name span { display: block; font-weight: 400; font-size: 15px; color: #4f5c66; }
        .scr { position: absolute; inset: 0; background: #f1f6f8; }
        .scr-body { padding: 20px 22px; }
"""

# ── Frame 3 — foundation one: open banking ──────────────────────────────────────
# agent-progress-theater (Reproduce): one trigger beat hands the frame to the machine,
# working-state runs, the receipt cascades in. The trigger fires INSIDE the carrier and
# the receipt detaches OUT of it.
rows = [("שופרסל דיל", "₪284.90"), ("FOX - פוקס", "₪1,000.00"), ("סופר-פארם", "₪129.40"),
        ("מקדונלד'ס", "₪64.00"), ("קסטרו", "₪319.90"), ("רמי לוי", "₪412.20")]
rows_html = "".join(
    '<div class="txn" id="f3-r%d"><span class="txn-name">%s</span>'
    '<span class="txn-amt num">%s</span></div>' % (i, n, a) for i, (n, a) in enumerate(rows))

stats = [("f3-st0", "142", "עסקאות"), ("f3-st1", "5,630", "₪ סכום כולל"), ("f3-st2", "3", "חשבונות")]
stats_html = "".join(
    '<div class="statcard" id="%s"><span class="stat-fig num" id="%s-n">0</span>'
    '<span class="stat-lab">%s</span></div>' % (i, i, l) for i, v, l in stats)

body = """
    <div id="f3-bg" class="ground g-dark clip" data-start="0" data-duration="6" data-track-index="0"></div>

    <div id="f3-scene" class="clip on-dark" data-start="0" data-duration="6" data-track-index="1">
      <div id="f3-stats" class="statrow">%(stats)s</div>
      %(dev)s
      <div class="cursor" id="f3-cur">%(cur)s</div>
      <div id="f3-line" class="words f3-head d1 band-a">%(l1)s<span class="mark"><span class="mark-bar" id="f3-bar"></span><span class="mark-ink">באמת</span></span><span> קניתם</span></div>
    </div>
""" % {"stats": stats_html, "cur": CURSOR_SVG,
       "l1": wordspans("Lessley רואה איפה"),
       "dev": device("f3", HEADER + """
          <div class="scr-body">
            <div class="bank-title">חיבור בנקאות פתוחה</div>
            <div class="bank-sub">כדי לפתוח את החיסכון האמיתי</div>
            <div class="bank-btn" id="f3-btn">חיבור הבנק שלי</div>
            <div class="txns" id="f3-txns">%s</div>
          </div>""" % rows_html)}

css = APP_CSS + """
        .f3-head { left: 72px; right: 72px; justify-content: flex-start; }
        .bank-title { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 30px; color: var(--ink); }
        .bank-sub { font-family: "Heebo", sans-serif; font-size: 17px; color: var(--muted); margin: 6px 0 18px; }
        .bank-btn { background: var(--primary); color: #fff; border-radius: 100px; text-align: center;
                    padding: 18px 0; font-family: "Heebo", sans-serif; font-weight: 700; font-size: 22px; }
        .txns { margin-top: 18px; }
        .txn { display: flex; justify-content: space-between; align-items: center; background: #fff;
               border: 1px solid #dde5e9; border-radius: 16px; padding: 14px 16px; margin-bottom: 10px; opacity: 0; }
        .txn-name { font-family: "Heebo", sans-serif; font-weight: 600; font-size: 19px; color: var(--ink); }
        .txn-amt { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 19px;
                   font-variant-numeric: tabular-nums; color: var(--muted); }
        .statrow { position: absolute; top: 400px; left: 72px; right: 72px; display: flex; gap: 18px; }
        .statcard { flex: 1; background: var(--dark-surface); border: 1.5px solid rgba(241,246,248,0.14);
                    border-radius: 28px; padding: 26px 18px; text-align: center; opacity: 0; }
        .stat-fig { display: block; font-family: "Heebo", sans-serif; font-weight: 800; font-size: 58px;
                    font-variant-numeric: tabular-nums; color: var(--dark-ink); line-height: 1; }
        .stat-lab { display: block; margin-top: 8px; font-family: "Heebo", sans-serif; font-weight: 600;
                    font-size: 22px; color: var(--dark-muted); }
        #f3-cur { left: 1180px; top: 980px; opacity: 0; }
"""

js = """
          /* Scene 1 (0.0–1.5s) — the carrier rises into frame and settles at rest. */
          tl.fromTo(el("f3-dev"), { y: 190, opacity: 0 },
                    { y: 0, opacity: 1, duration: 1.05, ease: "power3.out" }, 0.05);

          /* Scene 2 (1.5–2.6s) — the oversized cursor enters from off-frame and clicks.
             cursor-click-ripple: travel → depress with the target → ripple out. */
          tl.set(el("f3-cur"), { opacity: 1 }, 1.45);
          tl.fromTo(el("f3-cur"), { x: 0, y: 0 }, { x: -560, y: -300, duration: 0.72, ease: "power2.inOut" }, 1.48);
          tl.to(el("f3-cur"), { scale: 0.88, duration: 0.1, ease: "power2.in" }, 2.20);
          tl.to(el("f3-cur"), { scale: 1, duration: 0.26, ease: "power3.out" }, 2.30);
          tl.to(el("f3-btn"), { scale: 0.955, duration: 0.1, ease: "power2.in" }, 2.20);
          tl.to(el("f3-btn"), { scale: 1, duration: 0.34, ease: "power3.out" }, 2.30);
          tl.fromTo(el("f3-btn"), { boxShadow: "0 0 0 0 rgba(57,124,127,0.5)" },
                    { boxShadow: "0 0 0 26px rgba(57,124,127,0)", duration: 0.5, ease: "power2.out" }, 2.26);
          tl.to(el("f3-cur"), { opacity: 0, duration: 0.3, ease: "power2.out" }, 2.72);

          /* Scene 3 (2.6–4.6s) — the click ignites everything. Rows stream in right→left,
             then three stat cards DETACH out of the phone and count up. */
          for (var i = 0; i < 6; i++) { rise(el("f3-r" + i), 2.64 + i * 0.11, 0.4, 22); }
          var figs = [[el("f3-st0-n"), 142], [el("f3-st1-n"), 5630], [el("f3-st2-n"), 3]];
          for (var s = 0; s < 3; s++) {
            var card = el("f3-st" + s);
            /* card-morph-anchor: the card leaves the glass and stands alone, scaled up */
            tl.fromTo(card, { opacity: 0, scale: 0.42, y: 540 },
                      { opacity: 1, scale: 1, y: 0, duration: 0.78, ease: "power3.out" }, 3.24 + s * 0.16);
            countTo(figs[s][0], figs[s][1], 3.44 + s * 0.16, 0.86, 0.62);
          }

          /* Scene 4 (4.6–6.0s) — the receipt settles and holds. The claim itself was stated up
             front (Scene 1) because with no voiceover the text has to lead the visual. */
          words("#f3-line > span, #f3-line > .mark", 0.18, 0.085, 0.44, 30);
          sweep(el("f3-bar"), 0.86, 0.4);
          jitter(el("f3-stats"), 5.20, 0.75);
"""
print(emit("03-open-banking", body, css, js))


# ── Frame 4 — read-only ─────────────────────────────────────────────────────────
# grid-card-assemble (Adapt): the staggered self-assembly signature, but the array is
# three guarantee stamps and they assemble OVER the carried device — the phone must stay
# visible for the promise to be about IT.
STAMPS = ["בנקאות פתוחה מוסדרת", "גישה לקריאה בלבד", "השליטה נשארת אצלכם"]
stamps_html = "".join(
    '<div class="stamp" id="f4-s%d"><span class="stamp-ck">%s</span>'
    '<span class="stamp-tx">%s</span></div>' % (i, CHECK_SVG % "#397c7f", t)
    for i, t in enumerate(STAMPS))

body = """
    <div id="f4-bg" class="ground g-dark clip" data-start="0" data-duration="6" data-track-index="0"></div>

    <div id="f4-scene" class="clip on-dark" data-start="0" data-duration="6" data-track-index="1">
      %(dev)s
      <div id="f4-head" class="words f4-head d1 band-b"><span class="mark"><span class="mark-bar" id="f4-bar"></span><span class="mark-ink">לקריאה</span></span><span> בלבד</span></div>
      <div id="f4-stamps" class="stamps">%(stamps)s</div>
      <div id="f4-foot" class="f4-foot sup">היא לא יכולה להזיז שקל אחד.</div>
    </div>
""" % {"dev": device("f4", HEADER + """
          <div class="scr-body">
            <div class="bank-title">חיבור בנקאות פתוחה</div>
            <div class="bank-sub">כדי לפתוח את החיסכון האמיתי</div>
            <div class="bank-btn">חיבור הבנק שלי</div>
            <div class="bullets">
              <div class="bullet"><span class="bdot"></span>קריאת עסקאות בלבד</div>
              <div class="bullet"><span class="bdot"></span>אבטחה ברמה בנקאית</div>
              <div class="bullet"><span class="bdot"></span>ניתן לניתוק בכל רגע</div>
            </div>
            <div class="skip">דילוג לעת עתה</div>
            <div class="shield">
              <svg viewBox="0 0 64 72" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M32 3 L59 13 v24c0 17-11.5 27-27 32C16.5 64 5 54 5 37V13Z"
                      fill="#e4f2f1" stroke="#397c7f" stroke-width="2.6" stroke-linejoin="round"/>
                <rect x="21" y="31" width="22" height="16" rx="3.4" stroke="#397c7f" stroke-width="2.6"/>
                <path d="M25.5 31v-4.5a6.5 6.5 0 0 1 13 0V31" stroke="#397c7f" stroke-width="2.6"/>
                <circle cx="32" cy="39" r="2.4" fill="#397c7f"/>
              </svg>
              <span>קריאה בלבד</span>
            </div>
          </div>""", "opacity:1;"), "stamps": stamps_html}

css = APP_CSS + """
        .f4-head { left: 72px; right: 72px; justify-content: flex-start; }
        .stamps { position: absolute; top: 460px; left: 72px; right: 72px; }
        .stamp { display: flex; align-items: center; gap: 22px; background: rgba(241,246,248,0.96);
                 border-radius: 30px; padding: 26px 34px; margin-bottom: 20px; opacity: 0;
                 box-shadow: 0 20px 50px rgba(8,16,24,0.45); }
        .stamp-ck { width: 46px; height: 46px; flex: 0 0 46px; }
        .stamp-ck svg { width: 100%; height: 100%; }
        .stamp-tx { font-family: "Heebo", sans-serif; font-weight: 700; font-size: 38px; color: var(--ink); }
        .bullets { margin-top: 22px; }
        .bullet { display: flex; align-items: center; gap: 10px; font-family: "Heebo", sans-serif;
                  font-size: 17px; color: var(--ink); margin-bottom: 12px; }
        .bdot { width: 9px; height: 9px; border-radius: 50%; background: var(--primary); flex: 0 0 9px; }
        .skip { margin-top: 18px; text-align: center; font-family: "Heebo", sans-serif;
                font-size: 17px; color: #2b3238; text-decoration: underline; }
        .shield { margin-top: 40px; text-align: center; }
        .shield svg { width: 190px; height: 214px; display: block; margin: 0 auto; }
        .shield span { display: block; margin-top: 18px; font-family: "Heebo", sans-serif;
                       font-weight: 800; font-size: 30px; color: #14413d; }
        .f4-foot { position: absolute; top: 920px; left: 72px; right: 72px; opacity: 0;
                   background: var(--dark); border-radius: 24px; padding: 22px 30px; }
"""

js = """
          /* Scene 1 (0.0–1.2s) — the carrier is EXACTLY where frame 3 left it and does not
             move; it dims to ~45% and takes a soft defocus so the foreground owns the read.
             handoff_in: x540 y1040 scale 1 opacity 1 → dim only. */
          tl.set(el("f4-dev"), { opacity: 1 }, 0);
          tl.to(el("f4-dev"), { opacity: 0.72, filter: "blur(2px)", duration: 0.62, ease: "power2.out" }, 0.12);
          words("#f4-head > .mark, #f4-head > span", 0.12, 0.10, 0.5, 34);
          sweep(el("f4-bar"), 0.58, 0.42);

          /* Scene 2 (1.2–3.6s) — one stamp per bar (~0.8s at 100bpm ×2), right→left, each
             with its check self-drawing inside it. The pacing IS the music. */
          for (var i = 0; i < 3; i++) {
            var at = 1.22 + i * 0.80;
            tl.fromTo(el("f4-s" + i), { opacity: 0, x: 90, scale: 0.94 },
                      { opacity: 1, x: 0, scale: 1, duration: 0.56, ease: "power3.out" }, at);
            draw(ROOT.querySelector("#f4-s" + i + " .ck"), at + 0.2, 0.42);
          }

          /* Scene 3 (3.6–4.8s) */
          rise(el("f4-foot"), 3.66, 0.5, 26);

          /* Scene 4 (4.8–6.0s) — HELD FRAME (allocated in Video direction). Nothing moves
             but low-amplitude jitter. This is where a viewer decides whether to trust it. */
          jitter(el("f4-stamps"), 4.84, 1.1);
"""
print(emit("04-read-only", body, css, js))
