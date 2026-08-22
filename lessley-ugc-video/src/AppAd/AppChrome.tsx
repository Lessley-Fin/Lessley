import type { ReactNode } from "react";
import { Img, staticFile } from "remotion";
import { fontFamily } from "./font";

type Tab = "optimizer" | "insights" | "hot" | "recommend";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "optimizer", label: "Optimizer", icon: "✨" },
  { id: "insights", label: "Insights", icon: "📊" },
  { id: "hot", label: "Hot", icon: "🔥" },
  { id: "recommend", label: "Recommend", icon: "💡" },
];

/**
 * The app header and bottom tab bar from MainShell.tsx, at video scale.
 * Children render into the scrollable content area between them.
 */
export const AppChrome: React.FC<{ activeTab: Tab; children: ReactNode }> = ({
  activeTab,
  children,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        fontFamily,
        color: "#182634",
        backgroundColor: "#F5F9FB",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          height: 116,
          padding: "0 30px",
          backgroundColor: "rgba(255,255,255,0.94)",
          borderBottom: "1px solid #DDE5E9",
        }}
      >
        <Img
          src={staticFile("logo-without-name.svg")}
          style={{ width: 58, height: 58, flexShrink: 0 }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontSize: 27, fontWeight: 700, lineHeight: 1.15 }}>
            Lessley
          </p>
          <p style={{ margin: 0, fontSize: 19, color: "#687682", lineHeight: 1.3 }}>
            Financial autopilot
          </p>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 50,
            height: 50,
            borderRadius: 999,
            backgroundColor: "#D1F0EF",
            color: "#0C4A48",
            fontSize: 22,
            fontWeight: 700,
          }}
        >
          R
        </div>
      </div>

      <div
        style={{
          flex: 1,
          minHeight: 0,
          position: "relative",
          overflow: "hidden",
          padding: "26px 30px 0",
        }}
      >
        {children}
      </div>

      <div style={{ padding: "0 26px 26px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "stretch",
            justifyContent: "space-between",
            gap: 6,
            padding: 10,
            borderRadius: 999,
            background: "linear-gradient(150deg, #2A3B4F 0%, #1A2532 100%)",
            boxShadow: "0 8px 32px rgba(25,35,48,0.35)",
          }}
        >
          {TABS.map((tab) => (
            <div
              key={tab.id}
              style={{
                display: "flex",
                flex: 1,
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 3,
                padding: "12px 4px",
                borderRadius: 999,
                background:
                  tab.id === activeTab
                    ? "linear-gradient(135deg, #45939B 0%, #367680 100%)"
                    : "transparent",
                color: tab.id === activeTab ? "#F2FAFA" : "#A0ADB6",
                fontSize: 17,
                fontWeight: 600,
              }}
            >
              <span style={{ fontSize: 22, lineHeight: 1 }}>{tab.icon}</span>
              {tab.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
