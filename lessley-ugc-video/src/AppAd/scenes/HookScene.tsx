import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  Sequence,
  useCurrentFrame,
} from "remotion";
import { captionFontHe, fontFamily } from "../font";
import { HOOK_LINE, isRtl, MISSED_LABELS, type Language } from "../copy";

const MISSED = [
  { left: 96, from: 8 },
  { left: 560, from: 26 },
  { left: 210, from: 44 },
  { left: 640, from: 62 },
];

/** 0:00–0:05 — the hook, played tired rather than loud. */
export const HookScene: React.FC<{ language: Language }> = ({ language }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      name="Scene 1 - Hook"
      style={{ backgroundColor: "#0C1219" }}
    >
      <AbsoluteFill
        name="Cold glow"
        style={{
          background:
            "radial-gradient(circle at 50% 42%, rgba(52,80,102,0.5) 0%, rgba(52,80,102,0) 62%)",
        }}
      />

      {/* Savings slipping past, to make "missing out" literal. */}
      {MISSED.map((item, index) => (
        <Sequence
          key={item.left}
          name="Missed saving"
          layout="none"
          from={item.from}
        >
          <MissedChip
            label={MISSED_LABELS[language][index]}
            left={item.left}
            language={language}
          />
        </Sequence>
      ))}

      <AbsoluteFill
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: "100px 80px",
        }}
      >
        <Interactive.Div
          name="Hook line"
          style={{
            fontFamily: language === "he" ? captionFontHe : fontFamily,
            direction: isRtl(language) ? "rtl" : "ltr",
            fontSize: 104,
            fontWeight: 800,
            letterSpacing: "-0.04em",
            lineHeight: 1.08,
            color: "#E8EFF3",
            textAlign: "center",
            textShadow: "0 10px 40px rgba(0,0,0,0.6)",
            opacity: interpolate(frame, [6, 28], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
            scale: interpolate(frame, [6, 60], [1.14, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
              output: "perceptual-scale",
            }),
            translate: interpolate(frame, [6, 120], ["0px -12px", "0px 10px"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.4, 0, 0.6, 1),
            }),
          }}
        >
          {HOOK_LINE[language]}
        </Interactive.Div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const MissedChip: React.FC<{
  label: string;
  left: number;
  language: Language;
}> = ({ label, left, language }) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: "absolute",
        left,
        top: 0,
        padding: "14px 26px",
        borderRadius: 999,
        border: "2px solid rgba(148,175,190,0.28)",
        backgroundColor: "rgba(148,175,190,0.08)",
        fontFamily: language === "he" ? captionFontHe : fontFamily,
        direction: isRtl(language) ? "rtl" : "ltr",
        fontSize: 30,
        fontWeight: 600,
        color: "rgba(196,214,224,0.75)",
        whiteSpace: "nowrap",
        opacity: interpolate(frame, [0, 20, 62, 92], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: [
            Easing.bezier(0.16, 1, 0.3, 1),
            Easing.linear,
            Easing.bezier(0.4, 0, 0.6, 1),
          ],
        }),
        translate: interpolate(frame, [0, 92], ["0px 240px", "0px 1580px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.3, 0, 0.7, 1),
        }),
        rotate: interpolate(frame, [0, 92], ["-4deg", "5deg"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.linear,
        }),
      }}
    >
      {label}
    </div>
  );
};
