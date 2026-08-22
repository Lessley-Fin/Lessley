import { loadFont as loadHebrew } from "@remotion/google-fonts/NotoSansHebrew";
import { loadFont as loadRubik } from "@remotion/google-fonts/Rubik";
import { loadFont as loadJakarta } from "@remotion/google-fonts/PlusJakartaSans";

// The app itself ships Plus Jakarta Sans, so the mockups use the real typeface.
const jakarta = loadJakarta("normal", {
  weights: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

// Plus Jakarta Sans has no shekel sign (U+20AA) and renders it as tofu.
// Noto Sans Hebrew covers it and only ever gets used for that glyph.
const hebrew = loadHebrew("normal", {
  weights: ["400", "600", "700"],
  subsets: ["hebrew"],
});

export const fontFamily = `${jakarta.fontFamily}, ${hebrew.fontFamily}, sans-serif`;

// Plus Jakarta Sans has no Hebrew glyphs at all, so the Hebrew captions use
// Rubik — a Hebrew-first face that also carries the Latin "Lessley" wordmark.
const rubik = loadRubik("normal", {
  weights: ["400", "600", "800"],
  subsets: ["hebrew", "latin"],
});

export const captionFontHe = `${rubik.fontFamily}, ${hebrew.fontFamily}, sans-serif`;
