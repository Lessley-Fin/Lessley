import { Easing, Interactive, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../font";

const BANKS = ["Bank Hapoalim", "Isracard", "Max"];

/**
 * ConnectBankCard.tsx then ConnectionCheck.tsx — its own scene now (0:26–0:32),
 * so the consent screen and the sync each get time to land.
 */
export const OpenBankingScreen: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: "relative",
        height: "100%",
        fontFamily,
        color: "#182634",
      }}
    >
      {/* The consent card */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          opacity: interpolate(frame, [0, 18, 96, 112], [0, 1, 1, 0], {
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
        <p style={{ margin: 0, fontSize: 42, fontWeight: 800, letterSpacing: "-0.03em" }}>
          Your money, decoded
        </p>

        <div
          style={{
            marginTop: 26,
            padding: 32,
            borderRadius: 30,
            backgroundColor: "#FFFFFF",
            textAlign: "center",
            boxShadow: "0 1px 2px rgba(24,38,52,0.04), 0 8px 24px rgba(24,38,52,0.06)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 104,
              height: 104,
              margin: "0 auto",
              borderRadius: 999,
              backgroundColor: "#D1F0EF",
              fontSize: 48,
              scale: interpolate(frame, [0, 34], [0.6, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.spring({ damping: 12 }),
                output: "perceptual-scale",
              }),
            }}
          >
            🏦
          </div>
          <p style={{ margin: "24px 0 0", fontSize: 33, fontWeight: 700 }}>
            Connect your bank
          </p>
          <p
            style={{
              margin: "12px 0 0",
              fontSize: 22,
              lineHeight: 1.35,
              color: "#687682",
            }}
          >
            Link Open Banking to sync transactions and unlock personalized insights.
          </p>

          <Interactive.Div
            name="Connect Open Banking"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 94,
              marginTop: 28,
              borderRadius: 999,
              background: "linear-gradient(135deg, #45939B 0%, #367680 100%)",
              color: "#F2FAFA",
              fontSize: 26,
              fontWeight: 700,
              boxShadow: "0 12px 28px rgba(54,118,128,0.32)",
              scale: interpolate(frame, [74, 84, 96], [1, 0.955, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.bezier(0.4, 0, 0.6, 1),
                output: "perceptual-scale",
              }),
            }}
          >
            Connect Open Banking
          </Interactive.Div>

          <p style={{ margin: "20px 0 0", fontSize: 18, color: "#95A2AC" }}>
            Regulated Open Banking · Read-only access · You stay in control
          </p>
        </div>
      </div>

      {/* The sync */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 150,
          textAlign: "center",
          opacity: interpolate(frame, [104, 120], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 128,
            height: 128,
            margin: "0 auto",
            borderRadius: 999,
            backgroundColor: "#D1F0EF",
            fontSize: 58,
          }}
        >
          🔒
        </div>
        <p style={{ margin: "26px 0 0", fontSize: 31, fontWeight: 700 }}>
          Verifying bank connection…
        </p>
        <p style={{ margin: "10px 0 0", fontSize: 21, color: "#687682" }}>
          Read-only access · You stay in control
        </p>

        <div style={{ marginTop: 32 }}>
          {BANKS.map((bank, index) => (
            <div
              key={bank}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 14,
                padding: "22px 28px",
                borderRadius: 24,
                backgroundColor: "#FFFFFF",
                fontSize: 24,
                fontWeight: 600,
                boxShadow: "0 1px 2px rgba(24,38,52,0.04)",
                opacity: interpolate(
                  frame,
                  [112 + index * 14, 128 + index * 14],
                  [0.25, 1],
                  {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                    easing: Easing.bezier(0.16, 1, 0.3, 1),
                  },
                ),
              }}
            >
              {bank}
              <span style={{ color: "#2EB873", fontSize: 27 }}>
                {frame >= 136 + index * 14 ? "✓" : "…"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
