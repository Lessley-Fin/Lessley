import {
  AbsoluteFill,
  Easing,
  Img,
  Interactive,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { captionFontHe, fontFamily } from "../font";
import { CTA_LINE, isRtl, type Language } from "../copy";

/** 0:45–0:50 — the sign-off. */
export const CtaScene: React.FC<{ language: Language }> = ({ language }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill name="Scene 6 - CTA" style={{ backgroundColor: "#0B1119" }}>
      <AbsoluteFill
        name="Brand glow"
        style={{
          background:
            "radial-gradient(circle at 50% 40%, rgba(69,147,155,0.5) 0%, rgba(69,147,155,0) 58%)",
          opacity: interpolate(frame, [0, 30], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          scale: interpolate(frame, [0, 120], [0.88, 1.2], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.4, 0, 0.6, 1),
            output: "perceptual-scale",
          }),
        }}
      />

      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: 70,
          padding: "100px 80px",
        }}
      >
        <Img
          name="Brand logo"
          src={staticFile("logo-without-name.svg")}
          style={{
            width: 460,
            height: 460,
            filter: "drop-shadow(0 0 70px rgba(69,147,155,0.5))",
            opacity: interpolate(frame, [0, 20], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
            scale: interpolate(frame, [0, 44], [0.55, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.spring({ damping: 12 }),
              output: "perceptual-scale",
            }),
          }}
        />

        <Interactive.Div
          name="Sign-off"
          style={{
            fontFamily: language === "he" ? captionFontHe : fontFamily,
            direction: isRtl(language) ? "rtl" : "ltr",
            fontSize: 82,
            fontWeight: 800,
            letterSpacing: "-0.035em",
            lineHeight: 1.12,
            color: "#F2FAFA",
            textAlign: "center",
            opacity: interpolate(frame, [22, 44], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
            translate: interpolate(frame, [22, 58], ["0px 40px", "0px 0px"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.spring({ damping: 14 }),
            }),
          }}
        >
          {CTA_LINE[language]}
        </Interactive.Div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
