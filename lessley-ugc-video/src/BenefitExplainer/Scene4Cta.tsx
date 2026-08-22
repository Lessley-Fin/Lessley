import {
  AbsoluteFill,
  Easing,
  Img,
  Interactive,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { fontFamily } from "./font";

export const Scene4Cta: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      name="Scene 4 - Call to action"
      style={{ backgroundColor: "#07070C" }}
    >
      <AbsoluteFill
        name="Logo glow"
        style={{
          background:
            "radial-gradient(circle at 50% 40%, rgba(124,92,255,0.45) 0%, rgba(11,10,20,0) 55%)",
          opacity: interpolate(frame, [0, 40], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          scale: interpolate(frame, [0, 450], [0.9, 1.25], {
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
          gap: 110,
          padding: "100px 80px",
        }}
      >
        <Img
          name="Brand logo"
          src={staticFile("logo.png")}
          style={{
            width: 460,
            height: 460,
            filter: "drop-shadow(0 0 70px rgba(184,255,60,0.45))",
            opacity: interpolate(frame, [0, 22], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
            scale: interpolate(frame, [0, 46], [0.5, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.spring({ damping: 12 }),
              output: "perceptual-scale",
            }),
          }}
        />

        <Interactive.Div
          name="Call to action"
          style={{
            fontFamily,
            fontSize: 106,
            fontWeight: 900,
            letterSpacing: "-0.035em",
            lineHeight: 1.08,
            color: "#FFFFFF",
            textAlign: "center",
            opacity: interpolate(frame, [16, 40], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
            // Continuous looping bounce for the whole final 15 seconds.
            translate: `0px ${-Math.abs(Math.sin(frame / 11)) * 30}px`,
          }}
        >
          Stop overpaying.{" "}
          <span style={{ color: "#B8FF3C" }}>Download now.</span>
        </Interactive.Div>
      </AbsoluteFill>

      {/* Scene 3 ends on black - fade back up out of it. */}
      <AbsoluteFill
        name="Fade from black"
        style={{
          backgroundColor: "#000000",
          opacity: interpolate(frame, [0, 26], [1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.4, 0, 0.6, 1),
          }),
        }}
      />
    </AbsoluteFill>
  );
};
