import { Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../font";
import { ils } from "../helpers";

const CLUBS = [
  { name: "Hever", emoji: "🎟️", fit: 92, hit: 34, total: 40 },
  { name: "Isracard Fly Card", emoji: "✈️", fit: 78, hit: 22, total: 38 },
  { name: "Max Back", emoji: "💳", fit: 64, hit: 18, total: 44 },
  { name: "Cal Choice", emoji: "🛍️", fit: 51, hit: 14, total: 40 },
];

const MISSED = [
  {
    merchant: "Shufersal Deal",
    spent: 1240,
    purchases: 6,
    paidWith: "Credit · Isracard",
    club: "Hever",
  },
  {
    merchant: "Cafe Cafe",
    spent: 486,
    purchases: 12,
    paidWith: "Credit · Max",
    club: "Isracard Fly Card",
  },
  {
    merchant: "Paz Yellow",
    spent: 930.5,
    purchases: 4,
    paidWith: "Credit · Isracard",
    club: "Max Back",
  },
];

const BANDS = [
  { label: "Exact", count: 3 },
  { label: "Similar", count: 1 },
  { label: "Strong", count: 1 },
];

/** RecommendationsPage.tsx: top club matches, then the shops you already use. */
export const RecommendationsScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const onMissedTab = frame >= 158;

  return (
    <div style={{ fontFamily, color: "#182634" }}>
      <p style={{ margin: 0, fontSize: 42, fontWeight: 800, letterSpacing: "-0.03em" }}>
        Recommendations
      </p>
      <p style={{ margin: "6px 0 0", fontSize: 22, color: "#687682" }}>
        Club fit calculated from your last 90 days
      </p>

      {/* Tab pills, switched by the carousel below. */}
      <div
        style={{
          display: "flex",
          gap: 6,
          marginTop: 18,
          padding: 6,
          borderRadius: 999,
          border: "1px solid #DDE5E9",
          backgroundColor: "#FFFFFF",
        }}
      >
        {["Top matches", "Your shops"].map((tab, index) => (
          <div
            key={tab}
            style={{
              flex: 1,
              padding: "14px 8px",
              borderRadius: 999,
              textAlign: "center",
              fontSize: 21,
              fontWeight: 700,
              background:
                (index === 1) === onMissedTab
                  ? "linear-gradient(135deg, #45939B 0%, #367680 100%)"
                  : "transparent",
              color: (index === 1) === onMissedTab ? "#F2FAFA" : "#687682",
            }}
          >
            {tab}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 16, overflow: "hidden" }}>
        <div
          style={{
            display: "flex",
            gap: 16,
            width: 1332,
            translate: interpolate(
              frame,
              [150, 176],
              ["0px 0px", "-666px 0px"],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.bezier(0.22, 1, 0.36, 1),
              },
            ),
          }}
        >
          <TopClubMatches />
          <MissedShops />
        </div>
      </div>
    </div>
  );
};

const TopClubMatches: React.FC = () => {
  return (
    <div
      style={{
        flexShrink: 0,
        width: 650,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        padding: 26,
        borderRadius: 30,
        backgroundColor: "#FFFFFF",
        boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
        <span
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 52,
            height: 52,
            flexShrink: 0,
            borderRadius: 999,
            backgroundColor: "#D1F0EF",
            fontSize: 24,
          }}
        >
          ✨
        </span>
        <div>
          <p style={{ margin: 0, fontSize: 25, fontWeight: 700 }}>
            Top club matches
          </p>
          <p style={{ margin: "3px 0 0", fontSize: 18, color: "#687682" }}>
            Ranked by store overlap with your spend
          </p>
        </div>
      </div>

      <div>
        {CLUBS.map((club, index) => (
          <ClubRow key={club.name} club={club} index={index} />
        ))}
      </div>
    </div>
  );
};

const ClubRow: React.FC<{ club: (typeof CLUBS)[number]; index: number }> = ({
  club,
  index,
}) => {
  const frame = useCurrentFrame();
  const start = 16 + index * 16;

  return (
    <div
      style={{
        marginBottom: 12,
        padding: 18,
        borderRadius: 24,
        backgroundColor: "#EBF2F5",
        opacity: interpolate(frame, [start, start + 16], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        translate: interpolate(
          frame,
          [start, start + 28],
          ["-36px 0px", "0px 0px"],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 15 }),
          },
        ),
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <span
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 44,
            height: 44,
            flexShrink: 0,
            borderRadius: 999,
            backgroundColor: "#FFFFFF",
            fontSize: 20,
            fontWeight: 700,
          }}
        >
          {index + 1}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>
            {club.emoji} {club.name}
          </p>
          <p style={{ margin: "2px 0 0", fontSize: 18, color: "#687682" }}>
            {club.hit}/{club.total} stores match
          </p>
        </div>
        <span
          style={{
            flexShrink: 0,
            padding: "7px 16px",
            borderRadius: 999,
            backgroundColor: "#D1F0EF",
            color: "#0C4A48",
            fontSize: 20,
            fontWeight: 700,
          }}
        >
          {Math.round(
            interpolate(frame, [start + 8, start + 46], [0, club.fit], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
          )}
          %
        </span>
      </div>

      <div
        style={{
          height: 12,
          marginTop: 14,
          borderRadius: 999,
          backgroundColor: "#FFFFFF",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${club.fit}%`,
            borderRadius: 999,
            background: "linear-gradient(90deg, #45939B 0%, #367680 100%)",
            transformOrigin: "left center",
            scale: interpolate(frame, [start + 8, start + 46], ["0 1", "1 1"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
          }}
        />
      </div>
    </div>
  );
};

const MissedShops: React.FC = () => {
  return (
    <div
      style={{
        flexShrink: 0,
        width: 650,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 16,
          padding: 26,
          borderRadius: 30,
          backgroundColor: "#FFFFFF",
          boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
          <span
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 52,
              height: 52,
              flexShrink: 0,
              borderRadius: 999,
              backgroundColor: "#D1F0EF",
              fontSize: 24,
            }}
          >
            🏪
          </span>
          <div>
            <p style={{ margin: 0, fontSize: 25, fontWeight: 700 }}>
              Deals at shops you use
            </p>
            <p style={{ margin: "3px 0 0", fontSize: 18, color: "#687682" }}>
              5 stores you shopped at had matching deals
            </p>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: 6,
            padding: 6,
            borderRadius: 999,
            border: "1px solid #DDE5E9",
          }}
        >
          {BANDS.map((band) => (
            <div
              key={band.label}
              style={{
                flex: 1,
                padding: "12px 8px",
                borderRadius: 999,
                textAlign: "center",
                fontSize: 19,
                fontWeight: 600,
                background:
                  band.label === "Exact"
                    ? "linear-gradient(150deg, #2A3B4F 0%, #1A2532 100%)"
                    : "transparent",
                color: band.label === "Exact" ? "#EEF4F7" : "#687682",
              }}
            >
              {band.label} ({band.count})
            </div>
          ))}
        </div>
      </div>

      {MISSED.map((shop, index) => (
        <MissedCard key={shop.merchant} shop={shop} index={index} />
      ))}
    </div>
  );
};

const MissedCard: React.FC<{
  shop: (typeof MISSED)[number];
  index: number;
}> = ({ shop, index }) => {
  const frame = useCurrentFrame();
  const start = 182 + index * 16;

  return (
    <div
      style={{
        padding: 24,
        borderRadius: 30,
        backgroundColor: "#FFFFFF",
        boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
        opacity: interpolate(frame, [start, start + 16], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        translate: interpolate(
          frame,
          [start, start + 30],
          ["0px 46px", "0px 0px"],
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
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <p style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>{shop.merchant}</p>
        <span
          style={{
            flexShrink: 0,
            padding: "6px 14px",
            borderRadius: 999,
            backgroundColor: "rgba(46,184,115,0.14)",
            color: "#1E7A4C",
            fontSize: 17,
            fontWeight: 700,
          }}
        >
          Exact
        </span>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginTop: 14,
          fontSize: 19,
          color: "#687682",
        }}
      >
        <span>Total spent</span>
        <span style={{ fontSize: 24, fontWeight: 800, color: "#182634" }}>
          {ils(shop.spent)}
        </span>
      </div>

      <p style={{ margin: "10px 0 0", fontSize: 18, color: "#687682" }}>
        {shop.purchases} purchases · Paid with {shop.paidWith}
      </p>

      <span
        style={{
          display: "inline-block",
          marginTop: 14,
          padding: "8px 18px",
          borderRadius: 999,
          backgroundColor: "#EBF2F5",
          fontSize: 18,
          fontWeight: 600,
          color: "#33505C",
        }}
      >
        Through {shop.club}
      </span>
    </div>
  );
};
