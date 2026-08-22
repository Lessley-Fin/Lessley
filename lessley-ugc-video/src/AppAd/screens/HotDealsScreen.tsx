import { Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../font";

const DEALS = [
  {
    store: "Shufersal",
    category: "Groceries",
    title: "15% off your grocery bill",
    club: "Hever",
    badge: "−15%",
    emoji: "🛒",
  },
  {
    store: "Cafe Cafe",
    category: "Coffee & snacks",
    title: "1+1 on all hot drinks",
    club: "Isracard",
    badge: "1+1",
    emoji: "☕",
  },
  {
    store: "KSP",
    category: "Electronics",
    title: "₪300 off orders over ₪2,000",
    club: "Max",
    badge: "−₪300",
    emoji: "💻",
  },
];

/** HotDealsPage.tsx: the featured deal feed. */
export const HotDealsScreen: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        fontFamily,
        color: "#182634",
        translate: interpolate(frame, [56, 120], ["0px 0px", "0px -96px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.4, 0, 0.6, 1),
        }),
      }}
    >
      <p
        style={{
          margin: 0,
          fontSize: 42,
          fontWeight: 800,
          letterSpacing: "-0.03em",
        }}
      >
        Featured deals 🔥
      </p>
      <p style={{ margin: "6px 0 0", fontSize: 22, color: "#687682" }}>
        Real deals across your loyalty clubs
      </p>

      <div style={{ marginTop: 22 }}>
        {DEALS.map((deal, index) => (
          <DealCard key={deal.store} deal={deal} index={index} />
        ))}
      </div>
    </div>
  );
};

const DealCard: React.FC<{ deal: (typeof DEALS)[number]; index: number }> = ({
  deal,
  index,
}) => {
  const frame = useCurrentFrame();
  const start = 4 + index * 15;

  return (
    <div
      style={{
        marginBottom: 18,
        borderRadius: 30,
        overflow: "hidden",
        backgroundColor: "#FFFFFF",
        boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
        opacity: interpolate(frame, [start, start + 14], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        translate: interpolate(
          frame,
          [start, start + 28],
          ["0px 90px", "0px 0px"],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 15 }),
          },
        ),
      }}
    >
      <div
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 118,
          backgroundColor: "#FFFFFF",
          borderBottom: "1px solid #EEF3F6",
        }}
      >
        <span style={{ fontSize: 54, opacity: 0.35 }}>{deal.emoji}</span>
        <span
          style={{
            position: "absolute",
            left: 18,
            top: 18,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 40,
            height: 40,
            borderRadius: 999,
            backgroundColor: "#FFFFFF",
            boxShadow: "0 2px 8px rgba(24,38,52,0.16)",
            fontSize: 19,
            fontWeight: 700,
          }}
        >
          {index + 1}
        </span>
        <span
          style={{
            position: "absolute",
            right: 18,
            top: 18,
            padding: "8px 16px",
            borderRadius: 999,
            background: "linear-gradient(135deg, #F1A446 0%, #E08B2A 100%)",
            color: "#2A1A06",
            fontSize: 20,
            fontWeight: 800,
          }}
        >
          {deal.badge}
        </span>
      </div>

      <div style={{ padding: "20px 24px 22px" }}>
        <p style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{deal.store}</p>
        <p style={{ margin: "2px 0 0", fontSize: 18, color: "#687682" }}>
          {deal.category}
        </p>
        <p style={{ margin: "10px 0 0", fontSize: 24, fontWeight: 600, lineHeight: 1.25 }}>
          {deal.title}
        </p>
        <span
          style={{
            display: "inline-block",
            marginTop: 12,
            padding: "7px 16px",
            borderRadius: 999,
            backgroundColor: "#EBF2F5",
            fontSize: 18,
            fontWeight: 600,
            color: "#33505C",
          }}
        >
          {deal.club}
        </span>
      </div>
    </div>
  );
};
