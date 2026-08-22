# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,".hyperframes")
from fb import *

# ── Frame 13 — the close ────────────────────────────────────────────────────────
# logo-assemble-lockup (Adapt): keep the satellites-clear-and-the-mark-resolves-into-a-
# centred-lockup signature, extended to the CTA. The satellites are the SAME ten chips
# that opened the pain in frame 2, returning to the SAME scattered arrangement — so the
# collapse is a structural rhyme, not decoration: the thing that overwhelmed the viewer
# at 0:06 becomes the single card they now hold.
CHIPS = [
    ("mastercard_logo.jpg", 92, 150, 210), ("topcash_logo.png", 640, 96, 176),
    ("hever_giftcard_logo.jpg", 330, 372, 186), ("paisplus_logo.jpg", 726, 430, 168),
    ("hot_logo.png", 108, 610, 172), ("hever_teamim_logo.jpg", 560, 700, 190),
    ("paisplus_food_chains_logo.png", 830, 806, 160), ("swish_logo.png", 236, 900, 176),
    ("paisplus_networks_logo.jpg", 610, 1024, 168),
]
chips_html = "".join(
    '<div class="chipwrap13" id="f13-c%d" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;">'
    '<div class="chip" style="width:100%%;height:100%%;"><img src="assets/%s" alt="" /></div></div>'
    % (i, x, y, s, s, f) for i, (f, x, y, s) in enumerate(CHIPS))
chips_html += ('<div class="chipwrap13" id="f13-c9" style="left:300px;top:1180px;width:200px;height:172px;">'
               '<div class="chip name-chip13" style="width:100%;height:100%;">בהצדעה</div></div>')

body = """
    <div id="f13-bg" class="ground g-dark clip" data-start="0" data-duration="6" data-track-index="0"></div>

    <div id="f13-scene" class="clip stage on-dark" data-start="0" data-duration="6" data-track-index="1">
      <div id="f13-field">%(chips)s</div>
      <div id="f13-onecard" class="onecard"></div>
      <div id="f13-lock" class="lockup">
        <img class="lock-mark" src="assets/logo-without-name.svg" alt="" />
        <div class="lock-word">Lessley</div>
        <svg class="lock-rule" id="f13-rule" viewBox="0 0 600 4" xmlns="http://www.w3.org/2000/svg">
          <path class="ck" d="M600 2 L0 2" stroke="#397c7f" stroke-width="4" stroke-linecap="round" fill="none"/>
        </svg>
      </div>
      <div id="f13-tag" class="words tagline d2">%(tag)s</div>
      <div id="f13-cta" class="pill pill-teal ctapill">התחילו בחינם</div>
      <div id="f13-url" class="urlline"><span class="ltr">https://lessley.cs.colman.ac.il</span></div>
    </div>
""" % {"chips": chips_html, "tag": wordspans("טייס אוטומטי פיננסי לכל רכישה")}

css = """
        #f13-field { position: absolute; inset: 0; }
        .chipwrap13 { position: absolute; }
        .name-chip13 { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 34px;
                       color: var(--dark); background: #fff; }
        .onecard { position: absolute; left: 50%; top: 430px; width: 420px; height: 300px;
                   margin-left: -210px; border-radius: 42px; background: #fff; opacity: 0;
                   box-shadow: 0 34px 80px rgba(6,12,20,0.6); }
        .lockup { position: absolute; left: 0; right: 0; top: 400px; text-align: center; opacity: 0; }
        .lock-mark { width: 260px; height: 260px; object-fit: contain; display: block; margin: 0 auto; }
        .lock-word { margin-top: 18px; font-family: "Frank Ruhl Libre", serif; font-weight: 700;
                     font-size: 112px; letter-spacing: -0.03em; color: #ffffff; line-height: 1;
                     unicode-bidi: isolate; direction: ltr; }
        .lock-rule { display: block; width: 400px; height: 4px; margin: 34px auto 0; }
        .tagline { position: absolute; top: 940px; left: 0; right: 0; justify-content: center; }
        .ctapill { position: absolute; top: 1110px; left: 50%; transform: translateX(-50%);
                   font-size: 48px; font-weight: 800; padding: 28px 68px; opacity: 0; }
        .urlline { position: absolute; top: 1300px; left: 0; right: 0; text-align: center; opacity: 0;
                   font-family: "Heebo", sans-serif; font-weight: 600; font-size: 34px; color: var(--dark-muted); }
"""

js = """
          /* Scene 1 (0.0–1.6s) — the chips re-enter to the SAME positions they held in frame 2.
             The viewer recognises the arrangement before they can name why. */
          for (var i = 0; i < 10; i++) {
            var c = el("f13-c" + i);
            if (!c) continue;
            tl.fromTo(c, { opacity: 0, scale: 0.8 },
                      { opacity: 1, scale: 1, duration: 0.42, ease: "power3.out" }, 0.03 + i * 0.075);
          }

          /* Scene 2 (1.6–3.2s) — the chips COLLAPSE inward to one centre (the inverse of
             center-outward-expansion), each streaking slightly on the way in, while a single
             card scale-swaps into existence as they arrive. */
          var cx = 468, cy = 640;
          for (var k = 0; k < 10; k++) {
            var ch = el("f13-c" + k);
            if (!ch) continue;
            var lx = parseFloat(ch.style.left) + parseFloat(ch.style.width) / 2;
            var ly = parseFloat(ch.style.top) + parseFloat(ch.style.height) / 2;
            tl.to(ch, { x: cx - lx, y: cy - ly, scale: 0.34, opacity: 0, filter: "blur(6px)",
                        duration: 0.78, ease: "power2.in" }, 1.00 + (k % 5) * 0.05);
          }
          tl.fromTo(el("f13-onecard"), { opacity: 0, scale: 0.5 },
                    { opacity: 1, scale: 1, duration: 0.52, ease: "power3.out" }, 1.62);

          /* Scene 3 (3.2–4.4s) — the card resolves into the lockup; the rule self-draws
             right→left as it settles. */
          tl.to(el("f13-onecard"), { opacity: 0, scale: 1.3, duration: 0.4, ease: "power2.out" }, 2.28);
          tl.fromTo(el("f13-lock"), { opacity: 0, scale: 0.88 },
                    { opacity: 1, scale: 1, duration: 0.6, ease: "power3.out" }, 2.30);
          draw(ROOT.querySelector("#f13-rule .ck"), 2.76, 0.42);

          /* Scene 4 (4.4–5.4s) — the tagline, then the CTA and the URL. The URL is forced LTR
             inside its own isolation span so bidi cannot reorder it against the Hebrew. */
          words("#f13-tag > span", 3.10, 0.07, 0.44, 28);
          pop(el("f13-cta"), 3.68, 0.5, 0.88);
          fade(el("f13-url"), 4.04, 0.42);

          /* Scene 5 (5.4–6.0s) — HELD to the final frame. This is the video's only real exit;
             every other frame exits through its injected transition. */
          jitter(el("f13-lock"), 4.50, 1.4);
"""
print(emit("13-cta", body, css, js))
