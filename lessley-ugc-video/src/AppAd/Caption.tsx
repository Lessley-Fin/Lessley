import type { ReactNode } from "react";
import { Easing, Interactive, interpolate, useCurrentFrame } from "remotion";
import { captionFontHe, fontFamily } from "./font";
import { isRtl, type Language } from "./copy";

/**
 * The script line for a scene, sitting above the phone.
 * Rendered inside a <Sequence>, so frame 0 is the caption's own entrance.
 */
export const Caption: React.FC<{
  children: ReactNode;
  language: Language;
}> = ({ children, language }) => {
  const frame = useCurrentFrame();

  return (
    <Interactive.Div
      name="Caption"
      style={{
        position: "absolute",
        left: 80,
        right: 80,
        top: 108,
        fontFamily: language === "he" ? captionFontHe : fontFamily,
        direction: isRtl(language) ? "rtl" : "ltr",
        fontSize: 58,
        fontWeight: 800,
        letterSpacing: "-0.03em",
        lineHeight: 1.14,
        color: "#F4FAFB",
        textAlign: "center",
        textShadow: "0 6px 28px rgba(6,14,22,0.55)",
        opacity: interpolate(frame, [0, 12], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        translate: interpolate(frame, [0, 26], ["0px 42px", "0px 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.spring({ damping: 14 }),
        }),
      }}
    >
      {children}
    </Interactive.Div>
  );
};
