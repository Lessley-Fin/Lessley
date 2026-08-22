import { AbsoluteFill, Sequence } from "remotion";
import { Scene1Pain } from "./Scene1Pain";
import { Scene2Agitation } from "./Scene2Agitation";
import { Scene3Solution } from "./Scene3Solution";
import { Scene4Cta } from "./Scene4Cta";

// 1800 frames @ 30fps = 60 seconds, vertical 1080x1920.
export const BenefitExplainer: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#07070C" }}>
      {/* 0:00 - 0:10 */}
      <Sequence name="Scene 1 - Pain point"  durationInFrames={300}>
        <Scene1Pain />
      </Sequence>

      {/* 0:10 - 0:25, held 15 extra frames so Scene 3 can swipe down over it */}
      <Sequence name="Scene 2 - Agitation" from={300} durationInFrames={465}>
        <Scene2Agitation />
      </Sequence>

      {/* 0:25 - 0:45 */}
      <Sequence name="Scene 3 - Solution" from={750} durationInFrames={600}>
        <Scene3Solution />
      </Sequence>

      {/* 0:45 - 1:00 */}
      <Sequence name="Scene 4 - Call to action" from={1350} durationInFrames={450}>
        <Scene4Cta />
      </Sequence>
    </AbsoluteFill>
  );
};
