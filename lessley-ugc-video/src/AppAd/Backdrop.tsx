import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

/** The dark brand stage the phone sits on, so the light app UI pops. */
export const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill name="Backdrop">
      <AbsoluteFill
        style={{
          background: "linear-gradient(168deg, #1E2E3E 0%, #142030 52%, #0B1119 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 22%, rgba(69,147,155,0.42) 0%, rgba(69,147,155,0) 58%)",
          scale: interpolate(frame, [0, 1200], [1, 1.3], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.4, 0, 0.6, 1),
            output: "perceptual-scale",
          }),
        }}
      />
    </AbsoluteFill>
  );
};
