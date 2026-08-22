# -*- coding: utf-8 -*-
"""Shared scaffold for the 13 frame compositions.

Every frame file must be self-contained (sub-compositions are transport-cloned from
<template>, so styles cannot be linked), so this module inlines the same prelude into
each one. Authoring it once is what keeps 13 independently-written frames reading as one
film. Design truth is ../frame.md — token values here are copied from it, not invented.
"""
import os, io

W, H = 1080, 1920
SAFE_X, SAFE_TOP = 72, 120
KEEPOUT = 1594          # 0.83 * 1920 — nothing renders below this line
OUT = "compositions/frames"

HEB = "U+0307-0308, U+0590-05FF, U+200C-2010, U+20AA, U+25CC, U+FB1D-FB4F"
LAT = ("U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+2000-206F, U+20AC, "
       "U+2122, U+2191, U+2193, U+2212, U+2215")

def _faces():
    out = []
    for w in (400, 600, 800):
        out.append(f'@font-face{{font-family:"Heebo";font-style:normal;font-weight:{w};font-display:block;'
                   f'src:url("assets/fonts/heebo-{w}-hebrew.woff2") format("woff2");unicode-range:{HEB};}}')
        out.append(f'@font-face{{font-family:"Heebo";font-style:normal;font-weight:{w};font-display:block;'
                   f'src:url("assets/fonts/heebo-{w}-latin.woff2") format("woff2");unicode-range:{LAT};}}')
    out.append('@font-face{font-family:"Frank Ruhl Libre";font-style:normal;font-weight:700;font-display:block;'
               f'src:url("assets/fonts/frank-ruhl-libre-700-hebrew.woff2") format("woff2");unicode-range:{HEB};}}')
    out.append('@font-face{font-family:"Frank Ruhl Libre";font-style:normal;font-weight:700;font-display:block;'
               f'src:url("assets/fonts/frank-ruhl-libre-700-latin.woff2") format("woff2");unicode-range:{LAT};}}')
    return "\n        ".join(out)

SHARED_CSS = """
        /* ── faces: self-embedded, both subsets. The Latin subset carries the DIGITS,
              so dropping it would break every ₪ figure in the film. ──────────────── */
        %(faces)s

        /* ── tokens — copied from frame.md, never re-tinted ───────────────────── */
        #root {
          --bg: #f1f6f8;
          --ink: #182734;
          --muted: #687682;
          --primary: #397c7f;
          --accent-light: rgba(57,124,127,0.08);
          --accent-med: rgba(57,124,127,0.15);
          --brd: rgba(57,124,127,0.2);
          --card-bg: rgba(57,124,127,0.04);
          --mint: #d1f0ef;
          --mint-ink: #17544f;
          /* RATIONED — frames 01, 07, 13 only. --payoff is a FILL (dark ink rides on
             it); --payoff-ink is the same gold darkened for LARGE TEXT on cream, where
             the fill value only reaches 1.9:1. Contrast is a gate, not a preference. */
          --payoff: #f1a446;
          --payoff-ink: #a86a15;
          /* the second ground */
          --dark: #1d2c3a;
          --dark-ink: #f1f6f8;
          --dark-muted: #a0adb6;
          --dark-surface: #24384a;

          position: relative;
          width: %(W)dpx;
          height: %(H)dpx;
          overflow: hidden;
          /* RTL lives here, at container level. NEVER dir="rtl" on <html> — it renders
             the whole video black (confirmed failure in the sibling demo project). */
          direction: rtl;
          text-align: right;
          font-family: "Heebo", sans-serif;
          font-synthesis: none;
          -webkit-font-smoothing: antialiased;
        }

        /* Full-bleed grounds ride on a clip layer, never on #root — the frame root is
           clip-gated to its scene window, so a background on it is not a dependable ground. */
        .ground { position: absolute; inset: 0; }
        .g-cream { background: var(--bg); }
        .g-dark  { background: var(--dark); }

        /* the content region: top 83%%, side-safe */
        .stage {
          position: absolute;
          left: %(sx)dpx; right: %(sx)dpx; top: %(st)dpx;
          bottom: %(kb)dpx;
        }

        /* ── type ramp ────────────────────────────────────────────────────────── */
        .h1 { font-family: "Frank Ruhl Libre", serif; font-weight: 700; font-size: 104px;
              line-height: 1.06; letter-spacing: -0.02em; color: var(--ink); margin: 0; }
        .h2 { font-family: "Frank Ruhl Libre", serif; font-weight: 700; font-size: 78px;
              line-height: 1.12; letter-spacing: -0.02em; color: var(--ink); margin: 0; }
        .body { font-family: "Heebo", sans-serif; font-weight: 400; font-size: 40px;
                line-height: 1.5; color: var(--muted); margin: 0; }
        .label { font-family: "Heebo", sans-serif; font-weight: 600; font-size: 26px;
                 letter-spacing: 0.06em; color: var(--muted); margin: 0; }
        .fig { font-family: "Heebo", sans-serif; font-weight: 800; font-variant-numeric: tabular-nums;
               line-height: 1; color: var(--ink); display: inline-block; transform-origin: center center; }
        .on-dark .h1, .on-dark .h2 { color: var(--dark-ink); }
        .on-dark .body, .on-dark .label { color: var(--dark-muted); }


        /* ── THE RAMP — every frame draws from these. No per-frame font sizes. ──── */
        /* d1: the frame's single headline. d2: a quieter second display line.
           impact: the one-word slam (frame 2 only). Figures have four fixed steps. */
        .d1 { font-family: "Frank Ruhl Libre", serif; font-weight: 700; font-size: 88px;
              line-height: 1.14; letter-spacing: -0.02em; color: var(--ink); margin: 0; }
        .d2 { font-family: "Frank Ruhl Libre", serif; font-weight: 700; font-size: 64px;
              line-height: 1.2; letter-spacing: -0.02em; color: var(--ink); margin: 0; }
        .impact { font-family: "Frank Ruhl Libre", serif; font-weight: 700; font-size: 128px;
                  line-height: 1; letter-spacing: -0.03em; margin: 0; }
        .on-dark .d1, .on-dark .d2, .on-dark .impact { color: var(--dark-ink); }
        .sup { font-family: "Heebo", sans-serif; font-weight: 400; font-size: 40px;
               line-height: 1.5; color: var(--muted); margin: 0; }
        .on-dark .sup { color: var(--dark-muted); }
        .fig-hero   { font-size: 230px; letter-spacing: -0.03em; }
        .fig-payoff { font-size: 168px; }
        .fig-card   { font-size: 112px; }
        .fig-stat   { font-size: 58px; }

        /* Headline BANDS. Adjacent frames always sit on alternating tracks, so giving
           odd and even frames different bands means two headlines can never occupy the
           same line during a dissolve — which is what read as overlapping text. */
        .band-a { position: absolute; top: 130px; left: 0; right: 0; }
        .band-b { position: absolute; top: 300px; left: 0; right: 0; }

        /* Every figure is bidi-isolated so ₪700 can never render as 700₪. */
        .num { unicode-bidi: isolate; direction: ltr; display: inline-block; }
        /* Latin runs (brand names, the URL) inside Hebrew copy */
        .ltr { unicode-bidi: isolate; direction: ltr; display: inline-block; }

        /* per-word reveal: words are their own boxes so each can carry a tween */
        .words { display: flex; flex-wrap: wrap; gap: 0 0.28em; justify-content: flex-start; }
        .words > span { display: inline-block; will-change: transform, opacity; }

        /* marker sweep — grows from the RIGHT (RTL) and sits behind the word */
        .mark { position: relative; display: inline-block; }
        .mark > .mark-ink { position: relative; z-index: 1; }
        .mark > .mark-bar {
          position: absolute; z-index: 0; right: -0.08em; left: -0.08em;
          bottom: 0.04em; height: 0.42em; border-radius: 0.06em;
          background: var(--accent-med); transform-origin: right center;
        }
        .on-dark .mark > .mark-bar { background: rgba(57,124,127,0.55); }

        /* pills / chips / cards */
        .pill { display: inline-flex; align-items: center; gap: 14px; border-radius: 100px;
                padding: 18px 36px; font-family: "Heebo", sans-serif; font-weight: 600; font-size: 32px; }
        .pill-teal { background: var(--primary); color: #fff; }
        .pill-mint { background: var(--mint); color: var(--mint-ink); }
        .pill-gold { background: var(--payoff); color: #3a2408; }
        .card { background: #fff; border-radius: 34px; border: 1.5px solid var(--brd); }
        .card-tint { background: var(--card-bg); border: 1.5px solid var(--brd); border-radius: 34px; }
        .card-dark { background: var(--dark-surface); border-radius: 34px;
                     border: 1.5px solid rgba(241,246,248,0.12); }
        .chip { display: flex; align-items: center; justify-content: center;
                background: #fff; border-radius: 26px; overflow: hidden;
                box-shadow: 0 10px 30px rgba(12,22,32,0.28); }
        .chip img { width: 100%%; height: 100%%; object-fit: contain; padding: 12px; box-sizing: border-box; }

        /* the carried device — one size for the whole film; it never rescales */
        .device { position: absolute; width: 500px; height: 1084px; border-radius: 66px;
                  padding: 10px; box-sizing: border-box; background: #2a3038;
                  box-shadow: 0 40px 90px rgba(8,16,24,0.55); }
        .device-rim { position: absolute; inset: 0; border-radius: 66px;
                      border: 2px solid #9aa3ab; pointer-events: none; }
        .device-screen { position: relative; width: 100%%; height: 100%%; border-radius: 56px;
                         overflow: hidden; background: #f1f6f8; }
        .island { position: absolute; top: 12px; left: 50%%; margin-left: -68px; width: 136px;
                  height: 40px; border-radius: 20px; background: #14181c; z-index: 5; }

        /* oversized house cursor — enters from off-frame, never an OS cursor */
        .cursor { position: absolute; width: 76px; height: 76px; z-index: 40; }
""" % {"faces": _faces(), "W": W, "H": H, "sx": SAFE_X, "st": SAFE_TOP, "kb": H - KEEPOUT}

SHARED_JS = """
          var ID = "%(fid)s";
          var ROOT = document.querySelector('[data-composition-id="' + ID + '"]') || document;
          function el(id) { return ROOT.querySelector('[id="' + id + '"]'); }
          function all(sel) { return Array.prototype.slice.call(ROOT.querySelectorAll(sel)); }

          window.__timelines = window.__timelines || {};
          var tl = gsap.timeline({ paused: true });
          window.__timelines[ID] = tl;

          /* ── helpers — each reproduces a rule recipe from this frame's packet ──── */

          // dynamic-content-sequencing: binary opacity + a rise from below. Two fromTo
          // tweens at the same position keep the arrival crisp AND seek-safe.
          function rise(t, at, dur, off) {
            if (!t) return;
            tl.fromTo(t, { opacity: 0 }, { opacity: 1, duration: 0.001, ease: "none" }, at);
            tl.fromTo(t, { y: off === undefined ? 34 : off },
                         { y: 0, duration: dur === undefined ? 0.5 : dur, ease: "power4.out" }, at);
          }
          // per-word staggered reveal, RTL: DOM order === right-to-left order in an RTL flow,
          // so a plain forward stagger already fires right → left.
          function words(sel, at, step, dur, off) {
            var ws = all(sel);
            for (var i = 0; i < ws.length; i++) {
              rise(ws[i], at + i * (step === undefined ? 0.075 : step), dur, off);
            }
            return at + ws.length * (step === undefined ? 0.075 : step);
          }
          // spring-pop-entrance, SMOOTH-SETTLE register: power3.out, no overshoot.
          // The doctrine bans back/elastic/bounce as a default; this is the house entrance.
          function pop(t, at, dur, from) {
            if (!t) return;
            var s = from === undefined ? 0.88 : from;
            tl.fromTo(t, { opacity: 0, scale: s }, { opacity: 1, scale: 1,
              duration: dur === undefined ? 0.52 : dur, ease: "power3.out" }, at);
          }
          function fade(t, at, dur, to) {
            if (!t) return;
            tl.fromTo(t, { opacity: 0 }, { opacity: to === undefined ? 1 : to,
              duration: dur === undefined ? 0.5 : dur, ease: "power2.out" }, at);
          }
          // counting-dynamic-scale: value tween + a transform-scale growth sharing one
          // ease. font-size stays static CSS; only the transform changes per frame.
          function countTo(t, target, at, dur, startScale, fmt) {
            if (!t) return;
            var state = { v: 0 };
            tl.to(state, { v: target, duration: dur, ease: "power3.out",
              onUpdate: function () {
                t.textContent = fmt ? fmt(Math.round(state.v)) : Math.round(state.v).toLocaleString("en-US");
              } }, at);
            tl.fromTo(t, { scale: startScale === undefined ? 0.55 : startScale },
                         { scale: 1, duration: dur, ease: "power3.out" }, at);
          }
          // counting down — same recipe, non-zero start.
          function countFrom(t, from, target, at, dur, fmt) {
            if (!t) return;
            var state = { v: from };
            tl.to(state, { v: target, duration: dur, ease: "power3.out",
              onUpdate: function () {
                t.textContent = fmt ? fmt(Math.round(state.v)) : Math.round(state.v).toLocaleString("en-US");
              } }, at);
          }
          // css-marker-patterns: the highlight sweep, drawn RIGHT → LEFT (RTL).
          function sweep(t, at, dur) {
            if (!t) return;
            tl.fromTo(t, { scaleX: 0 }, { scaleX: 1,
              duration: dur === undefined ? 0.42 : dur, ease: "power2.inOut" }, at);
          }
          // svg-path-draw: stroke-dashoffset → 0.
          function draw(t, at, dur) {
            if (!t) return;
            var len = 0;
            try { len = t.getTotalLength(); } catch (e) { len = 400; }
            if (!len) len = 400;
            tl.set(t, { strokeDasharray: len, strokeDashoffset: len }, 0);
            tl.fromTo(t, { strokeDashoffset: len }, { strokeDashoffset: 0,
              duration: dur === undefined ? 0.5 : dur, ease: "power2.out" }, at);
          }
          // sine-wave-loop, LOW-AMPLITUDE register: the only sanctioned aliveness during a
          // hold. A finite tween chain over the hold — never repeat/yoyo (seek would break).
          function jitter(t, at, span) {
            if (!t) return;
            var steps = Math.max(2, Math.round(span / 0.42));
            for (var i = 0; i < steps; i++) {
              tl.to(t, { y: (i %% 2 === 0 ? -1.6 : 1.6), duration: span / steps, ease: "sine.inOut" },
                    at + i * (span / steps));
            }
          }
          // stat-bars-and-fills: the fill grows from the RIGHT edge (RTL).
          function fill(t, at, dur, to) {
            if (!t) return;
            tl.fromTo(t, { scaleX: 0 }, { scaleX: to === undefined ? 1 : to,
              duration: dur === undefined ? 0.9 : dur, ease: "power3.out" }, at);
          }
          // discrete-text-sequence: a hard cut, no fade — the swap itself is the beat.
          function hardcut(t, at) {
            if (!t) return;
            tl.fromTo(t, { opacity: 0 }, { opacity: 1, duration: 0.001, ease: "none" }, at);
          }
          function hardhide(t, at) {
            if (!t) return;
            tl.to(t, { opacity: 0, duration: 0.001, ease: "none" }, at);
          }
"""

CURSOR_SVG = ('<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
              '<path d="M5 2.5 L5 20.2 L9.6 15.9 L12.6 22.3 L15.9 20.8 L12.9 14.5 L19.2 14.2 Z" '
              'fill="#ffffff" stroke="#14181c" stroke-width="1.1" stroke-linejoin="round"/></svg>')

CHECK_SVG = ('<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
             '<path class="ck" d="M8 16.6 L13.6 22 L24 10.5" stroke="%s" stroke-width="3.4" '
             'stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>')

def wordspans(text, cls=""):
    """Split a Hebrew line into per-word spans. DOM order === RTL reading order."""
    c = (' class="%s"' % cls) if cls else ""
    return "".join("<span%s>%s</span>" % (c, w) for w in text.split(" ") if w)

def emit(fid, body, extra_css, js):
    html = (
        "<template>\n"
        "  <style>" + SHARED_CSS + "\n\n        /* ── frame-local ── */\n" + extra_css + "\n  </style>\n\n"
        '  <div id="root" data-composition-id="%s" data-width="%d" data-height="%d">\n' % (fid, W, H)
        + body + "\n  </div>\n\n"
        "  <script>\n    (function () {\n" + (SHARED_JS % {"fid": fid}) + "\n" + js + "\n    })();\n  </script>\n"
        "</template>\n"
    )
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, fid + ".html")
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path, len(html)
