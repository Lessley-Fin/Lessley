import { AbsoluteFill, Sequence } from "remotion";
import type { Language } from "./copy";
import { Music } from "./Music";
import { VoiceoverTrack } from "./VoiceoverTrack";
import { AppWalkthrough } from "./scenes/AppWalkthrough";
import { CtaScene } from "./scenes/CtaScene";
import { HookScene } from "./scenes/HookScene";

// 1770 frames @ 30fps = 59 seconds, vertical 1080x1920.
// Both language cuts share these scene boundaries exactly.
export const AppAd: React.FC<{ language: Language }> = ({ language }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0B1119" }}>
      <Music language={language} />
      <VoiceoverTrack language={language} />

      {/* 0:00 - 0:04 */}
      <Sequence name="Scene 1 - Hook" durationInFrames={120}>
        <HookScene language={language} />
      </Sequence>

      {/* 0:04 - 0:55 — login, optimizer, hot deals, open banking, insights, recommendations */}
      <Sequence name="Scenes 2-7 - App walkthrough" from={120} durationInFrames={1530}>
        <AppWalkthrough language={language} />
      </Sequence>

      {/* 0:55 - 0:59 */}
      <Sequence name="Scene 8 - CTA" from={1650} durationInFrames={120}>
        <CtaScene language={language} />
      </Sequence>
    </AbsoluteFill>
  );
};
