import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  Sequence,
  useCurrentFrame,
} from "remotion";
import { fontFamily } from "./font";

// A benefit banner that slides in from the left, holds, then slides back out.
const Benefit: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();

  return (
    <Interactive.Div
      name="Benefit banner"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 26,
        width: 920,
        padding: "34px 44px",
        borderRadius: 999,
        backgroundColor: "rgba(255,255,255,0.09)",
        border: "3px solid rgba(184,255,60,0.55)",
        fontFamily,
        fontSize: 52,
        fontWeight: 700,
        letterSpacing: "-0.02em",
        lineHeight: 1.15,
        color: "#FFFFFF",
        textAlign: "center",
        opacity: interpolate(frame, [0, 10, 132, 148], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: [
            Easing.bezier(0.16, 1, 0.3, 1),
            Easing.linear,
            Easing.bezier(0.5, 0, 0.75, 0),
          ],
        }),
        translate: interpolate(
          frame,
          [0, 22, 132, 150],
          ["-940px 0px", "0px 0px", "0px 0px", "-320px 0px"],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: [
              Easing.spring({ damping: 14 }),
              Easing.linear,
              Easing.bezier(0.5, 0, 0.75, 0),
            ],
          },
        ),
      }}
    >
      <span style={{ fontSize: 56, color: "#B8FF3C", fontWeight: 900 }}>✓</span>
      {children}
    </Interactive.Div>
  );
};

export const Scene3Solution: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    // The whole scene swipes down over Scene 2 to reveal itself.
    <AbsoluteFill
      name="Scene 3 - Solution"
      style={{
        translate: interpolate(frame, [0, 14], ["0px -1920px", "0px 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.22, 1, 0.36, 1),
        }),
      }}
    >
      <AbsoluteFill
        name="Gradient background"
        style={{
          background:
            "linear-gradient(196deg, #2E1C74 0%, #182A6B 38%, #0C3F55 72%, #073139 100%)",
        }}
      />
      <AbsoluteFill
        name="Brand glow"
        style={{
          background:
            "radial-gradient(circle at 50% 34%, rgba(184,255,60,0.34) 0%, rgba(184,255,60,0) 52%)",
          opacity: interpolate(frame, [14, 70, 300, 560], [0, 1, 0.85, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          scale: interpolate(frame, [14, 560], [0.85, 1.2], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.4, 0, 0.6, 1),
            output: "perceptual-scale",
          }),
        }}
      />

      <AbsoluteFill
        name="Content"
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: 90,
          padding: "100px 80px",
        }}
      >
        <Interactive.Div
          name="Wordmark"
          style={{
            fontFamily,
            fontSize: 158,
            fontWeight: 900,
            letterSpacing: "0.06em",
            lineHeight: 1,
            color: "#FFFFFF",
            textShadow:
              "0 0 40px rgba(184,255,60,0.95), 0 0 110px rgba(184,255,60,0.6), 0 0 200px rgba(124,92,255,0.65)",
            opacity: interpolate(frame, [14, 34], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
            scale: interpolate(frame, [14, 56], [0.55, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.spring({ damping: 12 }),
              output: "perceptual-scale",
            }),
          }}
        >
          LESSLEY
        </Interactive.Div>

        <Interactive.Div
          name="Benefit slot"
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            height: 260,
            width: "100%",
          }}
        >
          <Sequence
            name="Benefit 1"
            layout="none"
            from={120}
            durationInFrames={150}
          >
            <Benefit>AI-driven purchase optimization.</Benefit>
          </Sequence>
          <Sequence
            name="Benefit 2"
            layout="none"
            from={270}
            durationInFrames={150}
          >
            <Benefit>All your consumer club benefits in one place.</Benefit>
          </Sequence>
          <Sequence
            name="Benefit 3"
            layout="none"
            from={420}
            durationInFrames={150}
          >
            <Benefit>Never miss a discount again.</Benefit>
          </Sequence>
        </Interactive.Div>
      </AbsoluteFill>

      <AbsoluteFill
        name="Fade to black"
        style={{
          backgroundColor: "#000000",
          opacity: interpolate(frame, [548, 592], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.4, 0, 0.6, 1),
          }),
        }}
      />
    </AbsoluteFill>
  );
};
