import { Easing, Interactive, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../font";
import { ils, typed } from "../helpers";

const STEPS = [
  { title: "10% off groceries over ₪300", club: "Hever", percent: "8% off", saved: 99.2 },
  { title: "Isracard 5% cashback", club: "Isracard", percent: "5% off", saved: 62.0 },
  { title: "Shufersal Sale voucher", club: "Shufersal", percent: "7.8% off", saved: 96.2 },
];

const RANKED = [
  { rank: 2, price: 1009.4, saves: 230.6, deals: 2 },
  { rank: 3, price: 1041.6, saves: 198.4, deals: 2 },
];

/** OptimizerPage.tsx: enter a cart, stack deals, land on a final price. */
export const OptimizerScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const storeName = typed("Shufersal", frame, 20, 0.25);
  const cartTotal = typed("1240", frame, 64, 0.085);

  return (
    <div
      style={{
        fontFamily,
        color: "#182634",
        // Scrolls up once the result lands, the way a thumb would.
        translate: interpolate(
          frame,
          [150, 195, 335, 385],
          ["0px 0px", "0px -520px", "0px -520px", "0px -980px"],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.22, 1, 0.36, 1),
          },
        ),
      }}
    >
      <p style={{ margin: 0, fontSize: 42, fontWeight: 800, letterSpacing: "-0.03em" }}>
        Price optimizer
      </p>
      <p style={{ margin: "6px 0 0", fontSize: 22, color: "#687682" }}>
        AI-powered deal discovery ✨
      </p>

      <div
        style={{
          marginTop: 22,
          padding: 26,
          borderRadius: 30,
          backgroundColor: "#FFFFFF",
          boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "18px 24px",
            borderRadius: 22,
            backgroundColor: "#EBF2F5",
            fontSize: 23,
          }}
        >
          <span style={{ color: "#687682" }}>
            {storeName ? "Pricing against" : "Store name"}
          </span>
          <span style={{ fontWeight: 700 }}>{storeName}</span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            height: 92,
            marginTop: 16,
            padding: "0 26px",
            borderRadius: 24,
            border: cartTotal ? "2px solid #397C7F" : "2px solid #DDE5E9",
            fontSize: 27,
            color: cartTotal ? "#182634" : "#95A2AC",
            fontWeight: cartTotal ? 700 : 400,
          }}
        >
          {cartTotal ? `₪${cartTotal}` : "Total price ₪"}
        </div>

        <Interactive.Div
          name="Find best prices"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: 92,
            marginTop: 16,
            borderRadius: 999,
            background: "linear-gradient(135deg, #45939B 0%, #367680 100%)",
            color: "#F2FAFA",
            fontSize: 27,
            fontWeight: 700,
            boxShadow: "0 12px 28px rgba(54,118,128,0.32)",
            scale: interpolate(frame, [116, 126, 138], [1, 0.955, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.4, 0, 0.6, 1),
              output: "perceptual-scale",
            }),
          }}
        >
          {frame >= 126 && frame < 150 ? "Stacking deals…" : "Find best prices"}
        </Interactive.Div>
      </div>

      <div
        style={{
          marginTop: 22,
          borderRadius: 30,
          overflow: "hidden",
          backgroundColor: "#FFFFFF",
          boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
          opacity: interpolate(frame, [150, 172], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          translate: interpolate(frame, [150, 190], ["0px 70px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 14 }),
          }),
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            padding: 24,
            background: "linear-gradient(135deg, #45939B 0%, #367680 100%)",
            color: "#F2FAFA",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 50,
              height: 50,
              borderRadius: 999,
              backgroundColor: "rgba(255,255,255,0.22)",
              fontSize: 24,
            }}
          >
            🏆
          </div>
          <div>
            <p style={{ margin: 0, fontSize: 25, fontWeight: 700 }}>Best stack</p>
            <p style={{ margin: 0, fontSize: 19, opacity: 0.85 }}>
              Shufersal · 3 deals applied
            </p>
          </div>
        </div>

        <div style={{ padding: 26 }}>
          <p
            style={{
              margin: 0,
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#687682",
              textAlign: "center",
            }}
          >
            You pay
          </p>
          <p
            style={{
              margin: "8px 0 0",
              fontSize: 70,
              fontWeight: 800,
              letterSpacing: "-0.03em",
              color: "#397C7F",
              textAlign: "center",
            }}
          >
            {ils(
              interpolate(frame, [160, 225], [1240, 982.6], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.bezier(0.16, 1, 0.3, 1),
              }),
            )}
          </p>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              marginTop: 12,
            }}
          >
            <span
              style={{
                fontSize: 23,
                color: "#687682",
                textDecoration: "line-through",
              }}
            >
              {ils(1240)}
            </span>
            <span
              style={{
                padding: "8px 16px",
                borderRadius: 999,
                backgroundColor: "rgba(57,124,127,0.12)",
                fontSize: 20,
                fontWeight: 700,
                color: "#397C7F",
                opacity: interpolate(frame, [216, 234], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                }),
              }}
            >
              Save {ils(257.4)} (21%)
            </span>
          </div>

          <p
            style={{
              margin: "24px 0 12px",
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#687682",
            }}
          >
            How it stacks
          </p>

          {STEPS.map((step, index) => (
            <Step key={step.title} step={step} index={index} />
          ))}

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginTop: 12,
              padding: "16px 22px",
              borderRadius: 22,
              backgroundColor: "#EBF2F5",
              fontSize: 23,
            }}
          >
            <span style={{ fontWeight: 700 }}>You pay</span>
            <span style={{ fontSize: 26, fontWeight: 800, color: "#397C7F" }}>
              {ils(982.6)}
            </span>
          </div>
        </div>
      </div>

      {/* RankedOptions.tsx — the runner-up stacks, revealed by scrolling on. */}
      <div
        style={{
          marginTop: 22,
          padding: 26,
          borderRadius: 30,
          backgroundColor: "#FFFFFF",
          boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
          opacity: interpolate(frame, [330, 352], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#687682",
          }}
        >
          Other options
        </p>
        <p style={{ margin: "4px 0 16px", fontSize: 19, color: "#687682" }}>
          2 more ranked combinations
        </p>

        {RANKED.map((option, index) => (
          <RankedRow key={option.rank} option={option} index={index} />
        ))}
      </div>
    </div>
  );
};

const RankedRow: React.FC<{
  option: (typeof RANKED)[number];
  index: number;
}> = ({ option, index }) => {
  const frame = useCurrentFrame();
  const start = 342 + index * 16;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        marginBottom: 12,
        padding: 18,
        borderRadius: 24,
        border: "2px solid #DDE5E9",
        opacity: interpolate(frame, [start, start + 16], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        translate: interpolate(
          frame,
          [start, start + 28],
          ["0px 30px", "0px 0px"],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 15 }),
          },
        ),
      }}
    >
      <span
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 42,
          height: 42,
          flexShrink: 0,
          borderRadius: 999,
          backgroundColor: "#EBF2F5",
          fontSize: 19,
          fontWeight: 700,
        }}
      >
        {option.rank}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontSize: 23, fontWeight: 700 }}>
          {ils(option.price)}
        </p>
        <p style={{ margin: "2px 0 0", fontSize: 18, color: "#687682" }}>
          saves {ils(option.saves)} · {option.deals} deals
        </p>
      </div>
      <span style={{ flexShrink: 0, fontSize: 22, color: "#95A2AC" }}>⌄</span>
    </div>
  );
};

const Step: React.FC<{
  step: (typeof STEPS)[number];
  index: number;
}> = ({ step, index }) => {
  const frame = useCurrentFrame();
  const start = 172 + index * 18;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        marginBottom: 10,
        padding: 18,
        borderRadius: 22,
        backgroundColor: "#EBF2F5",
        opacity: interpolate(frame, [start, start + 14], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        translate: interpolate(
          frame,
          [start, start + 24],
          ["-40px 0px", "0px 0px"],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 14 }),
          },
        ),
      }}
    >
      <span
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 40,
          height: 40,
          flexShrink: 0,
          borderRadius: 999,
          background: "linear-gradient(135deg, #45939B 0%, #367680 100%)",
          color: "#F2FAFA",
          fontSize: 19,
          fontWeight: 700,
        }}
      >
        {index + 1}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontSize: 21, fontWeight: 600, lineHeight: 1.25 }}>
          {step.title}
        </p>
        <p style={{ margin: "4px 0 0", fontSize: 17, color: "#687682" }}>
          {step.club}
        </p>
      </div>
      <div style={{ flexShrink: 0, textAlign: "right" }}>
        <span
          style={{
            display: "block",
            padding: "6px 14px",
            borderRadius: 16,
            backgroundColor: "rgba(57,124,127,0.12)",
            fontSize: 19,
            fontWeight: 700,
            color: "#397C7F",
          }}
        >
          {step.percent}
        </span>
        <span
          style={{
            display: "block",
            marginTop: 5,
            fontSize: 18,
            fontWeight: 700,
            color: "#397C7F",
          }}
        >
          −{ils(step.saved)}
        </span>
      </div>
    </div>
  );
};
