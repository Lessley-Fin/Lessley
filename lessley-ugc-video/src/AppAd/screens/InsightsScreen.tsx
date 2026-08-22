import { Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../font";
import { ils, ilsWhole } from "../helpers";

const PERIODS = ["30 days", "90 days", "6 months", "Last year"];

const CATEGORIES = [
  { label: "🛒 Groceries", amount: 6240, color: "#397C7F" },
  { label: "🍽️ Restaurant", amount: 3180, color: "#4AABAB" },
  { label: "💻 Electronics", amount: 2460, color: "#80C6C2" },
  { label: "☕ Coffee & snacks", amount: 1720, color: "#385669" },
  { label: "⛽ Car & fuel", amount: 1410, color: "#F1A446" },
];

const TOP_STORES = [
  { name: "Shufersal", emoji: "🛒", count: 24, amount: 3120 },
  { name: "Cafe Cafe", emoji: "☕", count: 31, amount: 1840 },
  { name: "KSP", emoji: "💻", count: 4, amount: 1290 },
];

const TRANSACTIONS = [
  { name: "Shufersal Deal", date: "14 Aug", amount: 284.9 },
  { name: "Cafe Cafe", date: "13 Aug", amount: 42.0 },
  { name: "Paz Yellow", date: "12 Aug", amount: 310.5 },
];

const DOTS = [
  "Overview",
  "Categories",
  "Top stores",
  "Transactions",
  "Accounts",
  "Mix",
];

/**
 * InsightsRecommendationsPage.tsx once the bank is connected — savings hero,
 * stats grid, then the deep-dive carousel stepping right one slide at a time.
 * The connect/sync flow is its own scene now (OpenBankingScreen).
 */
export const InsightsScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const activeSlide = frame < 245 ? 0 : frame < 315 ? 1 : frame < 375 ? 2 : 3;

  return (
    <div
      style={{
        fontFamily,
        color: "#182634",
        opacity: interpolate(frame, [0, 18], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        translate: interpolate(
          frame,
          [0, 36, 122, 176],
          ["0px 60px", "0px 0px", "0px 0px", "0px -474px"],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: [
              Easing.spring({ damping: 15 }),
              Easing.linear,
              Easing.bezier(0.22, 1, 0.36, 1),
            ],
          },
        ),
      }}
    >
      <p style={{ margin: 0, fontSize: 42, fontWeight: 800, letterSpacing: "-0.03em" }}>
        Your money, decoded
      </p>
      <p style={{ margin: "6px 0 0", fontSize: 22, color: "#687682" }}>
        Last 90 days · 3 linked accounts
      </p>

      <PeriodPills />

      <div
        style={{
          marginTop: 16,
          padding: 30,
          borderRadius: 30,
          background: "linear-gradient(150deg, #2A3B4F 0%, #1A2532 100%)",
          color: "#EEF4F7",
          boxShadow: "0 8px 32px rgba(25,35,48,0.3)",
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#A0ADB6",
          }}
        >
          Saved with Lessley
        </p>
        <p style={{ margin: "12px 0 0", fontSize: 62, fontWeight: 800, letterSpacing: "-0.03em" }}>
          {ils(
            interpolate(frame, [24, 112], [0, 1284.5], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
          )}
        </p>
        <p style={{ margin: "10px 0 0", fontSize: 21, color: "#A0ADB6" }}>
          last 90 days · 4 clubs
        </p>
      </div>

      <div style={{ display: "flex", gap: 16, marginTop: 16 }}>
        <StatCard icon="🧾" label="Transactions" value="312" note="last 90 days" />
        <StatCard
          icon="👛"
          label="Total amount"
          value={ilsWhole(18420)}
          note="All linked cards"
        />
      </div>
      <p style={{ margin: "10px 4px 0", fontSize: 17, color: "#687682" }}>
        4 abroad · 6 in payments · 2 refunded
      </p>

      <div
        style={{
          marginTop: 22,
          paddingTop: 22,
          borderTop: "1px solid rgba(221,229,233,0.8)",
        }}
      >
        <p style={{ margin: 0, fontSize: 28, fontWeight: 800, letterSpacing: "-0.02em" }}>
          Deep dive
        </p>
        <p style={{ margin: "4px 0 0", fontSize: 20, color: "#687682" }}>
          Swipe through the details for the last 90 days.
        </p>
      </div>

      {/* Deep-dive carousel, stepping right one slide at a time. */}
      <div style={{ marginTop: 16, overflow: "hidden" }}>
        <div
          style={{
            display: "flex",
            gap: 16,
            width: 666 * DOTS.length,
            translate: interpolate(
              frame,
              [225, 245, 295, 315, 355, 375],
              [
                "0px 0px",
                "-666px 0px",
                "-666px 0px",
                "-1332px 0px",
                "-1332px 0px",
                "-1998px 0px",
              ],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.bezier(0.22, 1, 0.36, 1),
              },
            ),
          }}
        >
          <SlideCard title="Spending overview" subtitle="This period vs previous">
            <SpendingBars />
          </SlideCard>
          <SlideCard title="Top category" subtitle="Where the money goes">
            <CategoryBreakdown />
          </SlideCard>
          <SlideCard title="Top stores" subtitle="Scroll for the full ten">
            <StoreList />
          </SlideCard>
          <SlideCard title="Recent transactions" subtitle="Your latest activity">
            <TransactionList />
          </SlideCard>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 8,
          marginTop: 20,
        }}
      >
        {DOTS.map((label, index) => (
          <div
            key={label}
            style={{
              height: 8,
              width: index === activeSlide ? 34 : 8,
              borderRadius: 999,
              backgroundColor: index === activeSlide ? "#397C7F" : "#DDE5E9",
            }}
          />
        ))}
      </div>
    </div>
  );
};

const PeriodPills: React.FC = () => {
  return (
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
      {PERIODS.map((period) => (
        <div
          key={period}
          style={{
            flex: 1,
            padding: "14px 8px",
            borderRadius: 999,
            textAlign: "center",
            fontSize: 19,
            fontWeight: 600,
            background:
              period === "90 days"
                ? "linear-gradient(150deg, #2A3B4F 0%, #1A2532 100%)"
                : "transparent",
            color: period === "90 days" ? "#EEF4F7" : "#687682",
          }}
        >
          {period}
        </div>
      ))}
    </div>
  );
};

const StatCard: React.FC<{
  icon: string;
  label: string;
  value: string;
  note: string;
}> = ({ icon, label, value, note }) => {
  return (
    <div
      style={{
        flex: 1,
        padding: 24,
        borderRadius: 28,
        backgroundColor: "#FFFFFF",
        boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
      }}
    >
      <p
        style={{
          margin: 0,
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 17,
          fontWeight: 700,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "#687682",
        }}
      >
        <span style={{ fontSize: 19 }}>{icon}</span>
        {label}
      </p>
      <p style={{ margin: "10px 0 0", fontSize: 32, fontWeight: 800 }}>{value}</p>
      <p style={{ margin: "4px 0 0", fontSize: 17, color: "#687682" }}>{note}</p>
    </div>
  );
};

const SlideCard: React.FC<{
  title: string;
  subtitle: string;
  children: React.ReactNode;
}> = ({ title, subtitle, children }) => {
  return (
    <div
      style={{
        flexShrink: 0,
        width: 650,
        height: 430,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        padding: 26,
        borderRadius: 30,
        backgroundColor: "#FFFFFF",
        boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
      }}
    >
      <div>
        <p style={{ margin: 0, fontSize: 25, fontWeight: 700 }}>{title}</p>
        <p style={{ margin: "3px 0 0", fontSize: 18, color: "#687682" }}>
          {subtitle}
        </p>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>{children}</div>
    </div>
  );
};

const SpendingBars: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          gap: 34,
          paddingBottom: 14,
        }}
      >
        <Bar height={228} color="#2EB873" label={ilsWhole(16940)} delay={132} frame={frame} />
        <Bar height={248} color="#DF2033" label={ilsWhole(18420)} delay={142} frame={frame} />
      </div>
      <div style={{ display: "flex", gap: 22, fontSize: 17, color: "#687682" }}>
        <Legend color="#2EB873" text="16 Feb – 17 May" />
        <Legend color="#DF2033" text="18 May – 16 Aug" />
      </div>
    </div>
  );
};

const Bar: React.FC<{
  height: number;
  color: string;
  label: string;
  delay: number;
  frame: number;
}> = ({ height, color, label, delay, frame }) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 150,
        height,
        borderRadius: 14,
        backgroundColor: color,
        color: "#FFFFFF",
        fontSize: 19,
        fontWeight: 700,
        transformOrigin: "bottom center",
        scale: interpolate(frame, [delay, delay + 30], ["1 0", "1 1"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
      }}
    >
      {label}
    </div>
  );
};

const Legend: React.FC<{ color: string; text: string }> = ({ color, text }) => {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span
        style={{ width: 12, height: 12, borderRadius: 999, backgroundColor: color }}
      />
      {text}
    </span>
  );
};

const CategoryBreakdown: React.FC = () => {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20, height: "100%" }}>
      <div
        style={{
          flexShrink: 0,
          width: 196,
          height: 196,
          borderRadius: 999,
          // Donut, matching the recharts pie on the real slide.
          background:
            "conic-gradient(#397C7F 0deg 122deg, #4AABAB 124deg 184deg, #80C6C2 186deg 233deg, #385669 235deg 265deg, #F1A446 267deg 296deg, #EBF2F5 298deg 360deg)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: 112,
            height: 112,
            borderRadius: 999,
            backgroundColor: "#FFFFFF",
          }}
        />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {CATEGORIES.map((category) => (
          <div
            key={category.label}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 10,
              marginBottom: 12,
              fontSize: 19,
            }}
          >
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                minWidth: 0,
                overflow: "hidden",
                whiteSpace: "nowrap",
              }}
            >
              <span
                style={{
                  flexShrink: 0,
                  width: 12,
                  height: 12,
                  borderRadius: 999,
                  backgroundColor: category.color,
                }}
              />
              {category.label}
            </span>
            <span style={{ flexShrink: 0, fontWeight: 700 }}>
              {ilsWhole(category.amount)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const StoreList: React.FC = () => {
  return (
    <div>
      {TOP_STORES.map((store, index) => (
        <div
          key={store.name}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            marginBottom: 10,
            padding: 16,
            borderRadius: 22,
            backgroundColor: "#EBF2F5",
          }}
        >
          <span
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 46,
              height: 46,
              flexShrink: 0,
              borderRadius: 999,
              backgroundColor: "#FFFFFF",
              fontSize: 22,
            }}
          >
            {store.emoji}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ margin: 0, fontSize: 21, fontWeight: 700 }}>
              {index + 1}. {store.name}
            </p>
            <p style={{ margin: "2px 0 0", fontSize: 17, color: "#687682" }}>
              {store.count} transactions
            </p>
          </div>
          <span style={{ flexShrink: 0, fontSize: 21, fontWeight: 700 }}>
            {ilsWhole(store.amount)}
          </span>
        </div>
      ))}
    </div>
  );
};

const TransactionList: React.FC = () => {
  return (
    <div>
      {TRANSACTIONS.map((transaction) => (
        <div
          key={transaction.name}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            marginBottom: 10,
            padding: 16,
            borderRadius: 22,
            backgroundColor: "#EBF2F5",
          }}
        >
          <div style={{ minWidth: 0 }}>
            <p style={{ margin: 0, fontSize: 21, fontWeight: 700 }}>
              {transaction.name}
            </p>
            <p style={{ margin: "2px 0 0", fontSize: 17, color: "#687682" }}>
              {transaction.date}
            </p>
          </div>
          <span style={{ flexShrink: 0, fontSize: 21, fontWeight: 700 }}>
            {ils(transaction.amount)}
          </span>
        </div>
      ))}
    </div>
  );
};
