import type { ReactNode } from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { AppChrome } from "./AppChrome";

type Tab = "optimizer" | "insights" | "hot" | "recommend";

/**
 * One app screen inside the phone, with the tab bar on the right tab and a
 * short entrance so switching screens reads as navigation.
 */
export const PhoneScreen: React.FC<{ activeTab: Tab; children: ReactNode }> = ({
  activeTab,
  children,
}) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        opacity: interpolate(frame, [0, 10], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        translate: interpolate(frame, [0, 22], ["44px 0px", "0px 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.22, 1, 0.36, 1),
        }),
      }}
    >
      <AppChrome activeTab={activeTab}>{children}</AppChrome>
    </div>
  );
};
