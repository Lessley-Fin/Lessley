import { Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../font";
import { ils } from "../helpers";

const TERMS = [
  "Minimum purchase ₪300",
  "Groceries only, excludes tobacco",
  "Valid until 31 Dec 2026",
];

/**
 * DealInfoDialog.tsx — the modal that opens from a stack step.
 * Rendered as a sibling of the app chrome so the scrim covers the whole screen,
 * the way a real dialog does.
 */
export const DealDialog: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 40,
        fontFamily,
        color: "#182634",
        backgroundColor: "rgba(12,20,28,0.55)",
        opacity: interpolate(frame, [0, 10, 78, 95], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: [
            Easing.bezier(0.16, 1, 0.3, 1),
            Easing.linear,
            Easing.bezier(0.4, 0, 0.6, 1),
          ],
        }),
      }}
    >
      <div
        style={{
          width: "100%",
          padding: 30,
          borderRadius: 34,
          backgroundColor: "#FFFFFF",
          boxShadow: "0 24px 60px rgba(8,16,24,0.4)",
          scale: interpolate(frame, [0, 22], [0.86, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 14 }),
            output: "perceptual-scale",
          }),
          translate: interpolate(frame, [0, 22], ["0px 34px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 14 }),
          }),
        }}
      >
        <p style={{ margin: 0, fontSize: 27, fontWeight: 800, lineHeight: 1.2 }}>
          10% off groceries over ₪300
        </p>
        <p style={{ margin: "8px 0 0", fontSize: 19, color: "#687682" }}>
          Club deal · Hever
        </p>

        <div
          style={{
            marginTop: 22,
            padding: 20,
            borderRadius: 22,
            backgroundColor: "#EBF2F5",
          }}
        >
          <Row label="Discount applies to" value={ils(1240)} />
          <Row label="You pay on it" value={ils(1140.8)} />
          <Row label="Saved here" value={`−${ils(99.2)}`} accent />
        </div>

        <p
          style={{
            margin: "22px 0 10px",
            fontSize: 17,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#687682",
          }}
        >
          Terms
        </p>
        {TERMS.map((term) => (
          <p
            key={term}
            style={{
              margin: "0 0 8px",
              display: "flex",
              gap: 10,
              fontSize: 19,
              color: "#33505C",
            }}
          >
            <span style={{ color: "#397C7F" }}>•</span>
            {term}
          </p>
        ))}

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: 76,
            marginTop: 20,
            borderRadius: 999,
            background: "linear-gradient(135deg, #45939B 0%, #367680 100%)",
            color: "#F2FAFA",
            fontSize: 22,
            fontWeight: 700,
          }}
        >
          Open deal ↗
        </div>
      </div>
    </div>
  );
};

const Row: React.FC<{ label: string; value: string; accent?: boolean }> = ({
  label,
  value,
  accent,
}) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        gap: 12,
        marginBottom: 8,
        fontSize: 20,
      }}
    >
      <span style={{ color: "#687682" }}>{label}</span>
      <span
        style={{
          fontWeight: 700,
          color: accent ? "#397C7F" : "#182634",
        }}
      >
        {value}
      </span>
    </div>
  );
};
