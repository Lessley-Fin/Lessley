import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  Sequence,
  useCurrentFrame,
} from "remotion";
import { fontFamily } from "./font";

// One word of the headline. Rendered inside a <Sequence>, so its own clock
// starts at 0 when the word is supposed to pop in.
const Word: React.FC<{ children: React.ReactNode; color: string }> = ({
  children,
  color,
}) => {
  const frame = useCurrentFrame();

  return (
    <Interactive.Div
      name="Word"
      style={{
        fontFamily,
        fontSize: 128,
        fontWeight: 900,
        letterSpacing: "-0.035em",
        lineHeight: 1.02,
        color,
        opacity: interpolate(frame, [0, 6], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        scale: interpolate(frame, [0, 18], [0.4, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.spring({ damping: 11 }),
          output: "perceptual-scale",
        }),
        translate: interpolate(frame, [0, 18], ["0px 48px", "0px 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.spring({ damping: 11 }),
        }),
      }}
    >
      {children}
    </Interactive.Div>
  );
};

export const Scene1Pain: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill name="Scene 1 - Pain point" style={{ backgroundColor: "#07070C" }}>
      <AbsoluteFill
        name="Ambient glow"
        style={{
          background:
            "radial-gradient(circle at 50% 38%, rgba(124,92,255,0.42) 0%, rgba(124,92,255,0) 58%)",
          opacity: interpolate(frame, [0, 60, 200, 300], [0.5, 1, 1, 0.35], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          scale: interpolate(frame, [0, 300], [1, 1.35], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.4, 0, 0.6, 1),
            output: "perceptual-scale",
          }),
        }}
      />

      {/* Everything scales up into the camera from 8s until the scene ends. */}
      <AbsoluteFill
        name="Headline block"
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: "100px 80px",
          scale: interpolate(frame, [240, 300], [1, 34], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.6, 0, 0.95, 0.4),
            output: "perceptual-scale",
          }),
          opacity: interpolate(frame, [268, 296], [1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.6, 0, 0.9, 0.4),
          }),
        }}
      >
        <Interactive.Div
          name="Headline"
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            alignItems: "baseline",
            columnGap: 26,
            rowGap: 6,
            textAlign: "center",
          }}
        >
          <Sequence name="Word 1" layout="none" from={20}>
            <Word color="#FFFFFF">Tired</Word>
          </Sequence>
          <Sequence name="Word 2" layout="none" from={42}>
            <Word color="#FFFFFF">of</Word>
          </Sequence>
          <Sequence name="Word 3" layout="none" from={64}>
            <Word color="#FFFFFF">missing</Word>
          </Sequence>
          <Sequence name="Word 4" layout="none" from={86}>
            <Word color="#FFFFFF">out</Word>
          </Sequence>
          <Sequence name="Word 5" layout="none" from={108}>
            <Word color="#FFFFFF">on</Word>
          </Sequence>
          <Sequence name="Word 6" layout="none" from={130}>
            <Word color="#B8FF3C">club</Word>
          </Sequence>
          <Sequence name="Word 7" layout="none" from={152}>
            <Word color="#B8FF3C">discounts?</Word>
          </Sequence>
        </Interactive.Div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
