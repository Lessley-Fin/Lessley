import { Composition, Folder } from "remotion";
import "./index.css";
import { AppAd } from "./AppAd/AppAd";
import { AppWalkthrough } from "./AppAd/scenes/AppWalkthrough";
import { CtaScene } from "./AppAd/scenes/CtaScene";
import { HookScene } from "./AppAd/scenes/HookScene";
import { BenefitExplainer } from "./BenefitExplainer/BenefitExplainer";
import { Scene1Pain } from "./BenefitExplainer/Scene1Pain";
import { Scene2Agitation } from "./BenefitExplainer/Scene2Agitation";
import { Scene3Solution } from "./BenefitExplainer/Scene3Solution";
import { Scene4Cta } from "./BenefitExplainer/Scene4Cta";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="LessleyAppAd"
        component={AppAd}
        durationInFrames={1770}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ language: "en" as const }}
      />
      <Composition
        id="LessleyAppAdHe"
        component={AppAd}
        durationInFrames={1770}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ language: "he" as const }}
      />

      <Folder name="LessleyAppAd-Scenes">
        <Composition
          id="AppAd-Hook"
          component={HookScene}
          durationInFrames={120}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ language: "en" as const }}
        />
        <Composition
          id="AppAd-Walkthrough"
          component={AppWalkthrough}
          durationInFrames={1530}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ language: "en" as const }}
        />
        <Composition
          id="AppAd-Cta"
          component={CtaScene}
          durationInFrames={120}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ language: "en" as const }}
        />
      </Folder>

      <Folder name="Archive-BenefitExplainer">
        <Composition
          id="BenefitExplainer"
          component={BenefitExplainer}
          durationInFrames={1800}
          fps={30}
          width={1080}
          height={1920}
        />
        <Composition
          id="Scene1Pain"
          component={Scene1Pain}
          durationInFrames={300}
          fps={30}
          width={1080}
          height={1920}
        />
        <Composition
          id="Scene2Agitation"
          component={Scene2Agitation}
          durationInFrames={465}
          fps={30}
          width={1080}
          height={1920}
        />
        <Composition
          id="Scene3Solution"
          component={Scene3Solution}
          durationInFrames={600}
          fps={30}
          width={1080}
          height={1920}
        />
        <Composition
          id="Scene4Cta"
          component={Scene4Cta}
          durationInFrames={450}
          fps={30}
          width={1080}
          height={1920}
        />
      </Folder>
    </>
  );
};
