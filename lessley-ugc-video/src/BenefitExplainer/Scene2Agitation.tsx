import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { fontFamily } from "./font";

export const Scene2Agitation: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      name="Scene 2 - Agitation"
      style={{ backgroundColor: "#FFD84D" }}
    >
      <AbsoluteFill
        name="Warning stripes"
        style={{
          background:
            "repeating-linear-gradient(-45deg, rgba(11,10,20,0.07) 0px, rgba(11,10,20,0.07) 60px, rgba(11,10,20,0) 60px, rgba(11,10,20,0) 120px)",
          width: 2400,
          height: 2600,
          left: -400,
          top: -300,
          translate: interpolate(frame, [0, 465], ["0px 0px", "170px 170px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.linear,
          }),
        }}
      />

      <AbsoluteFill
        name="Copy block"
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: "100px 80px",
        }}
      >
        <Interactive.Div
          name="Agitation copy"
          style={{
            fontFamily,
            fontSize: 116,
            fontWeight: 900,
            letterSpacing: "-0.035em",
            lineHeight: 1.06,
            color: "#0B0A14",
            textAlign: "center",
            opacity: interpolate(frame, [0, 10], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
            scale: interpolate(frame, [0, 24], [0.7, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.spring({ damping: 12 }),
              output: "perceptual-scale",
            }),
            // Frustration shake - a deliberate Math.sin wobble on rotation.
            rotate: `${Math.sin(frame / 2.6) * 1.5}deg`,
            translate: `${Math.sin(frame / 1.7) * 6}px ${Math.sin(frame / 3.4) * 5}px`,
          }}
        >
          You are probably{" "}
          <span
            style={{
              color: "#E01B3C",
              textDecoration: "underline",
              textDecorationThickness: 12,
              textUnderlineOffset: 16,
            }}
          >
            overpaying
          </span>{" "}
          at retail stores every single day.
        </Interactive.Div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
