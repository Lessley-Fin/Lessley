import {
  AbsoluteFill,
  Easing,
  interpolate,
  Sequence,
  useCurrentFrame,
} from "remotion";
import { Backdrop } from "../Backdrop";
import { Caption } from "../Caption";
import { CAPTIONS, type Language } from "../copy";
import { PhoneFrame } from "../PhoneFrame";
import { PhoneScreen } from "../PhoneScreen";
import { DealDialog } from "../screens/DealDialog";
import { HotDealsScreen } from "../screens/HotDealsScreen";
import { InsightsScreen } from "../screens/InsightsScreen";
import { LoginScreen } from "../screens/LoginScreen";
import { OpenBankingScreen } from "../screens/OpenBankingScreen";
import { OptimizerScreen } from "../screens/OptimizerScreen";
import { RecommendationsScreen } from "../screens/RecommendationsScreen";

/**
 * 0:04–0:55 — one continuous session in the app. The phone stays put while the
 * screens and the script lines change around it.
 *
 * Local frames (this scene starts at global frame 120):
 *   0–120 login · 120–540 optimizer · 540–660 hot deals
 *   660–840 open banking · 840–1230 insights · 1230–1530 recommendations
 *
 * The app screens are identical in both languages; only the captions and the
 * voice track change.
 */
export const AppWalkthrough: React.FC<{ language: Language }> = ({
  language,
}) => {
  const frame = useCurrentFrame();
  const copy = CAPTIONS[language];

  return (
    <AbsoluteFill name="App walkthrough">
      <Backdrop />

      <Sequence name="Line - Meet Lessley" durationInFrames={120}>
        <Caption language={language}>{copy["02-meet"]}</Caption>
      </Sequence>
      <Sequence name="Line - Which card" from={120} durationInFrames={150}>
        <Caption language={language}>{copy["03a-assume"]}</Caption>
      </Sequence>
      <Sequence name="Line - Best price" from={270} durationInFrames={270}>
        <Caption language={language}>{copy["03b-calculates"]}</Caption>
      </Sequence>
      <Sequence name="Line - Hot deals" from={540} durationInFrames={120}>
        <Caption language={language}>{copy["04-hot"]}</Caption>
      </Sequence>
      <Sequence name="Line - Open banking" from={660} durationInFrames={180}>
        <Caption language={language}>{copy["05-banking"]}</Caption>
      </Sequence>
      {/* One spoken take, two caption cards — the sentence is too long for one. */}
      <Sequence name="Line - Insights a" from={840} durationInFrames={200}>
        <Caption language={language}>{copy["06a-insights"]}</Caption>
      </Sequence>
      <Sequence name="Line - Insights b" from={1040} durationInFrames={190}>
        <Caption language={language}>{copy["06b-insights"]}</Caption>
      </Sequence>
      <Sequence name="Line - Use recommendations" from={1230} durationInFrames={180}>
        <Caption language={language}>{copy["07a-use"]}</Caption>
      </Sequence>
      <Sequence name="Line - Purchasing power" from={1410} durationInFrames={120}>
        <Caption language={language}>{copy["07b-power"]}</Caption>
      </Sequence>

      <AbsoluteFill
        name="Phone"
        style={{
          opacity: interpolate(frame, [0, 18], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          translate: interpolate(frame, [0, 40], ["0px 200px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 16 }),
          }),
        }}
      >
        <PhoneFrame>
          <Sequence name="Screen - Login" durationInFrames={120}>
            <LoginScreen />
          </Sequence>
          <Sequence name="Screen - Optimizer" from={120} durationInFrames={420}>
            <PhoneScreen activeTab="optimizer">
              <OptimizerScreen />
            </PhoneScreen>
          </Sequence>
          {/* Opens on top of the optimizer, over the chrome, like a real dialog. */}
          <Sequence name="Deal dialog" from={360} durationInFrames={90}>
            <DealDialog />
          </Sequence>
          <Sequence name="Screen - Hot deals" from={540} durationInFrames={120}>
            <PhoneScreen activeTab="hot">
              <HotDealsScreen />
            </PhoneScreen>
          </Sequence>
          <Sequence name="Screen - Open banking" from={660} durationInFrames={180}>
            <PhoneScreen activeTab="insights">
              <OpenBankingScreen />
            </PhoneScreen>
          </Sequence>
          <Sequence name="Screen - Insights" from={840} durationInFrames={390}>
            <PhoneScreen activeTab="insights">
              <InsightsScreen />
            </PhoneScreen>
          </Sequence>
          <Sequence
            name="Screen - Recommendations"
            from={1230}
            durationInFrames={300}
          >
            <PhoneScreen activeTab="recommend">
              <RecommendationsScreen />
            </PhoneScreen>
          </Sequence>
        </PhoneFrame>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
