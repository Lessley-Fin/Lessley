import type { ReactNode } from "react";
import { AbsoluteFill } from "remotion";

/**
 * The device the app mockups live inside.
 * Screen is 710x1400 at 165,380 in the 1080x1920 canvas.
 */
export const PhoneFrame: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <AbsoluteFill name="Phone frame">
      <div
        style={{
          position: "absolute",
          left: 165,
          top: 380,
          width: 750,
          height: 1440,
          borderRadius: 76,
          padding: 20,
          background: "linear-gradient(160deg, #33414F 0%, #141B23 100%)",
          boxShadow:
            "0 40px 90px rgba(6,14,22,0.55), 0 0 0 2px rgba(255,255,255,0.06) inset",
        }}
      >
        <div
          style={{
            position: "relative",
            width: 710,
            height: 1400,
            borderRadius: 58,
            overflow: "hidden",
            backgroundColor: "#F5F9FB",
          }}
        >
          {children}
        </div>
      </div>
    </AbsoluteFill>
  );
};
