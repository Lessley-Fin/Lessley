# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,".hyperframes")
from fb import *
exec(open(".hyperframes/b2.py",encoding="utf-8").read().split("# ── Frame 3")[0].split("from fb import *")[1])

# ── Frame 5 — the optimizer input ───────────────────────────────────────────────
# cursor-ui-demo (Reproduce): a visible cursor drives a reconstructed UI through real
# state changes on a locked stage; the element swaps do the camera work.
body = """
    <div id="f5-bg" class="ground g-cream clip" data-start="0" data-duration="5" data-track-index="0"></div>

    <div id="f5-scene" class="clip" data-start="0" data-duration="5" data-track-index="1">
      <div id="f5-q" class="words f5-head d1 band-a">%(q)s</div>
      %(dev)s
      <div class="cursor" id="f5-cur">%(cur)s</div>
    </div>
""" % {"q": wordspans("כמה תשלמו בפועל?"), "cur": CURSOR_SVG,
       "dev": device("f5", HEADER + """
          <div class="scr-body">
            <div class="opt-title">אופטימיזציית מחיר</div>
            <div class="opt-sub">גילוי דילים מונע בינה מלאכותית</div>
            <div class="field" id="f5-f1"><span class="fld-lab">שם חנות</span><span class="fld-val" id="f5-store"></span><span class="caret" id="f5-car1"></span></div>
            <div class="field" id="f5-f2"><span class="fld-lab">מחיר כולל ₪</span><span class="fld-val num" id="f5-price"></span><span class="caret" id="f5-car2"></span></div>
            <div class="field field-sel"><span class="fld-lab">מקסימום דילים בשילוב</span>
              <span class="fld-val" id="f5-max1">דיל אחד</span><span class="fld-val swapped" id="f5-max2">3 דילים</span></div>
            <div class="opt-btn" id="f5-btn"><span id="f5-btl">מציאת המחירים הטובים ביותר</span><span id="f5-bt2" class="swapped">משלבים דילים…</span></div>
            <div class="spinrow" id="f5-spin"><i></i><i></i><i></i></div>
          </div>""")}

css = APP_CSS + """
        .f5-head { left: 72px; right: 72px; justify-content: flex-start; }
        .opt-title { font-family: "Heebo", sans-serif; font-weight: 800; font-size: 30px; color: var(--ink); }
        .opt-sub { font-family: "Heebo", sans-serif; font-size: 16px; color: var(--muted); margin: 4px 0 20px; }
        .field { position: relative; background: #fff; border: 1.5px solid #dde5e9; border-radius: 18px;
                 padding: 12px 16px; margin-bottom: 12px; min-height: 54px; box-sizing: border-box; }
        .fld-lab { display: block; font-family: "Heebo", sans-serif; font-size: 14px; color: var(--muted); }
        .fld-val { font-family: "Heebo", sans-serif; font-weight: 700; font-size: 22px; color: var(--ink); }
        .field-sel .fld-val { display: inline-block; }
        .swapped { opacity: 0; position: absolute; right: 16px; bottom: 12px; }
        .caret { display: inline-block; width: 2px; height: 24px; background: var(--primary);
                 vertical-align: -4px; margin-right: 3px; opacity: 0; }
        .opt-btn { position: relative; background: var(--primary); color: #fff; border-radius: 100px;
                   text-align: center; padding: 18px 0; font-family: "Heebo", sans-serif;
                   font-weight: 700; font-size: 21px; margin-top: 6px; }
        .opt-btn .swapped { right: 0; left: 0; bottom: 18px; }
        .spinrow { display: flex; gap: 10px; justify-content: center; margin-top: 20px; opacity: 0; }
        .spinrow i { width: 12px; height: 12px; border-radius: 50%; background: var(--primary); display: block; }
        #f5-cur { left: 300px; top: 1180px; opacity: 0; }
"""

js = """
          /* Scene 1 (0.0–1.0s) — the ground is cream now; the carrier brightens back in place
             (handoff_in: no move, no rescale — only 0.45 → 1.0 and the defocus clears). */
          tl.fromTo(el("f5-dev"), { opacity: 0.72, filter: "blur(2px)" },
                    { opacity: 1, filter: "blur(0px)", duration: 0.62, ease: "power2.out" }, 0);
          tl.set(el("f5-cur"), { opacity: 1 }, 0.86);

          /* Scene 2 (1.0–2.2s) — type-on with caret, right→left. discrete-text-sequence:
             the text is built one character at a time, never faded in. */
          function typeInto(target, caret, text, at, dur) {
            var st = { n: 0 };
            tl.to(st, { n: text.length, duration: dur, ease: "none",
              onUpdate: function () { target.textContent = text.slice(0, Math.round(st.n)); } }, at);
            /* context-sensitive-cursor: a square-wave blink, deterministic — no repeat */
            tl.set(caret, { opacity: 1 }, at);
            for (var b = 0; b < 6; b++) { tl.set(caret, { opacity: b % 2 ? 1 : 0.15 }, at + b * 0.16); }
            tl.set(caret, { opacity: 0 }, at + dur + 0.1);
          }
          tl.fromTo(el("f5-cur"), { x: 0, y: 0 }, { x: 40, y: -560, duration: 0.5, ease: "power2.inOut" }, 0.9);
          typeInto(el("f5-store"), el("f5-car1"), "FOX - פוקס", 1.05, 0.62);

          /* Scene 3 (2.2–3.2s) */
          tl.to(el("f5-cur"), { y: -490, duration: 0.34, ease: "power2.inOut" }, 1.98);
          typeInto(el("f5-price"), el("f5-car2"), "₪1,000", 2.22, 0.5);
          /* the selector STEPS — a discrete token swap, not a fade */
          hardhide(el("f5-max1"), 2.92); hardcut(el("f5-max2"), 2.92);

          /* Scene 4 (3.2–4.2s) — press-release-spring: compress, then spring recovery, and
             the label hard-cuts into the working state. */
          tl.to(el("f5-cur"), { x: -30, y: -300, duration: 0.36, ease: "power2.inOut" }, 3.12);
          tl.to(el("f5-btn"), { scale: 0.955, duration: 0.1, ease: "power2.in" }, 3.48);
          tl.to(el("f5-btn"), { scale: 1, duration: 0.36, ease: "power3.out" }, 3.58);
          tl.to(el("f5-cur"), { scale: 0.88, duration: 0.1, ease: "power2.in" }, 3.48);
          tl.to(el("f5-cur"), { scale: 1, duration: 0.3, ease: "power3.out" }, 3.58);
          hardhide(el("f5-btl"), 3.62); hardcut(el("f5-bt2"), 3.62);
          tl.to(el("f5-cur"), { opacity: 0, duration: 0.28, ease: "power2.out" }, 3.9);
          fade(el("f5-spin"), 3.66, 0.3);
          /* the working state runs THROUGH the cut — the question is left unanswered here */
          var dots = all("#f5-spin i");
          for (var d = 0; d < dots.length; d++) {
            for (var p = 0; p < 4; p++) {
              tl.to(dots[d], { opacity: p % 2 ? 1 : 0.3, duration: 0.16, ease: "sine.inOut" },
                    3.72 + p * 0.16 + d * 0.06);
            }
          }

          /* Scene 5 (4.2–5.0s) */
          words("#f5-q > span", 0.14, 0.09, 0.44, 32);
"""
print(emit("05-optimizer-input", body, css, js))


# ── Frame 6 — THE ENGINE (the film's most differentiating shot) ──────────────────
# constellation-hub (Adapt): keep the nodes-spring-into-a-ring-then-resolve-on-the-core
# signature. What changes is WHY the orbit collapses — not a click, but ELIMINATION.
# Each rejected node folds out carrying its real engine reason, so the collapse is the
# solver's reasoning made visible.
NODES = [("mastercard_logo.jpg", -300, -170), ("topcash_logo.png", 300, -170),
         ("hever_giftcard_logo.jpg", 0, -300), ("paisplus_food_chains_logo.png", -330, 130),
         ("paisplus_networks_logo.jpg", 330, 130), ("hot_logo.png", -170, 300),
         ("swish_logo.png", 170, 300)]
nodes_html = "".join(
    '<div class="node" id="f6-n%d" style="margin-left:%dpx;margin-top:%dpx;">'
    '<div class="chip" style="width:100%%;height:100%%;"><img src="assets/%s" alt="" /></div></div>'
    % (i, x - 70, y - 70, f) for i, (f, x, y) in enumerate(NODES))

body = """
    <div id="f6-bg" class="ground g-dark clip" data-start="0" data-duration="8" data-track-index="0"></div>

    <div id="f6-scene" class="clip on-dark" data-start="0" data-duration="8" data-track-index="1">
      <div id="f6-head" class="words f6-head d1 band-b">%(h)s</div>
      <div id="f6-orbit" class="orbit">
        <svg class="conn" viewBox="-540 -420 1080 840" xmlns="http://www.w3.org/2000/svg">
          <path id="f6-p0" d="M -300 -170 L 300 -170" stroke="rgba(57,124,127,0.85)" stroke-width="3" fill="none"/>
          <path id="f6-p1" d="M -330 130 L 330 130" stroke="rgba(57,124,127,0.85)" stroke-width="3" fill="none"/>
          <path id="f6-p2" d="M 0 -300 L -170 300" stroke="rgba(57,124,127,0.85)" stroke-width="3" fill="none"/>
        </svg>
        <div class="cartfig num" id="f6-cart">₪1,000</div>
        %(nodes)s
        <div class="rej" id="f6-rj0">לא ניתן לשלב</div>
        <div class="rej" id="f6-rj1">קבוצה בלעדית</div>
        <div class="rej" id="f6-rj2">לא ניתן לשלב</div>
      </div>
      <div id="f6-c1" class="f6-close d2">רוב הצירופים לא <span class="mark"><span class="mark-bar" id="f6-bar"></span><span class="mark-ink">חוקיים.</span></span></div>
      <div id="f6-c2" class="f6-close2 sup">הוא יודע בדיוק אילו.</div>
    </div>
""" % {"h": wordspans("המנוע בודק כל צירוף אפשרי"), "nodes": nodes_html}

css = """
        .f6-head { left: 72px; right: 72px; justify-content: flex-start; }
        .orbit { position: absolute; left: 50%; top: 880px; width: 0; height: 0; }
        .conn { position: absolute; left: -540px; top: -420px; width: 1080px; height: 840px; overflow: visible; }
        .node { position: absolute; left: 0; top: 0; width: 140px; height: 140px; }
        .cartfig { position: absolute; left: -190px; top: -60px; width: 380px; text-align: center;
                   font-family: "Heebo", sans-serif; font-weight: 800; font-size: 112px;
                   font-variant-numeric: tabular-nums; color: var(--dark-ink); }
        .rej { position: absolute; background: #2b1c1c; color: #ff9b9b; border: 1.5px solid #6b3535;
               border-radius: 100px; padding: 8px 20px; font-family: "Heebo", sans-serif;
               font-weight: 700; font-size: 26px; opacity: 0; white-space: nowrap; }
        #f6-rj0 { left: -110px; top: -230px; }
        #f6-rj1 { left: -110px; top: 100px; }
        #f6-rj2 { left: -420px; top: 190px; }
        .f6-close { position: absolute; top: 1290px; left: 72px; right: 72px; opacity: 0; }
        .f6-close2 { position: absolute; top: 1385px; left: 72px; right: 72px; opacity: 0; }
"""

js = """
          /* handoff_in: ₪1,000 survives the cut from frame 5 at the same centre. */
          tl.set(el("f6-cart"), { opacity: 1 }, 0);

          /* Scene 1 (0.0–1.6s) — orbit-3d-entry: nodes flip in from 3D space and settle
             into their orbital positions, staggered right→left. Far-side nodes carry a
             static depth blur so the ring reads as real space. */
          var N = 7;
          for (var i = 0; i < N; i++) {
            var n = el("f6-n" + i);
            tl.fromTo(n, { opacity: 0, rotationY: -74, scale: 0.62 },
                      { opacity: 1, rotationY: 0, scale: 1, duration: 0.62, ease: "power3.out" },
                      0.08 + i * 0.14);
            if (i === 5 || i === 6) tl.set(n, { filter: "blur(3px)", opacity: 0.7 }, 0);
          }

          /* Scene 2 (1.6–3.0s) — the claim, then connectors self-draw between tested pairs,
             one pair per beat: the engine trying combinations. */
          words("#f6-head > span", 1.60, 0.08, 0.44, 28);
          draw(el("f6-p0"), 2.20, 0.34);
          draw(el("f6-p1"), 2.52, 0.34);
          draw(el("f6-p2"), 2.84, 0.34);

          /* Scene 3 (3.0–5.4s) — ELIMINATION, one per bar. The connector snaps, the real
             engine reason hard-cuts in, and both nodes fold and fall with a velocity smear.
             Truth: the two PaisPlus FOX deals share exclusive_group paisplus:chit-5001 and
             one is stackable_with_giftcards:false — so the real solver rejects them. */
          var FAILS = [[3.05, "f6-p0", ["f6-n0", "f6-n1"], "f6-rj0"],
                       [3.85, "f6-p1", ["f6-n3", "f6-n4"], "f6-rj1"],
                       [4.65, "f6-p2", ["f6-n5", "f6-n6"], "f6-rj2"]];
          for (var f = 0; f < FAILS.length; f++) {
            var at = FAILS[f][0];
            tl.to(el(FAILS[f][1]), { opacity: 0, duration: 0.12, ease: "power2.in" }, at);
            hardcut(el(FAILS[f][3]), at + 0.06);
            tl.to(el(FAILS[f][3]), { opacity: 0, duration: 0.18, ease: "power2.in" }, at + 0.62);
            for (var k = 0; k < 2; k++) {
              var nd = el(FAILS[f][2][k]);
              tl.to(nd, { rotationZ: k ? 24 : -24, duration: 0.2, ease: "power2.in" }, at + 0.24);
              tl.to(nd, { y: 620, opacity: 0, scaleY: 1.22, filter: "blur(9px)",
                          duration: 0.5, ease: "power2.in" }, at + 0.34);
            }
          }

          /* Scene 4 (5.4–7.0s) — one node left. scale-swap-transition: the survivor takes
             the centre as the remains of the ring shrink away. */
          tl.to(el("f6-n2"), { x: 0, y: 300, scale: 1.35, duration: 0.86, ease: "power3.out" }, 5.42);
          tl.to(el("f6-cart"), { y: -150, scale: 0.82, duration: 0.86, ease: "power3.out" }, 5.42);

          /* Scene 5 (7.0–8.0s) — the close, on two beats, with the marker sweep. */
          rise(el("f6-c1"), 5.62, 0.46, 30);
          sweep(el("f6-bar"), 6.02, 0.4);
          rise(el("f6-c2"), 6.10, 0.44, 26);
          jitter(el("f6-orbit"), 7.10, 0.85);
"""
print(emit("06-the-engine", body, css, js))
