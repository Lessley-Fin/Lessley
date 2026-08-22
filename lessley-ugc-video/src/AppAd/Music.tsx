import { Audio } from "@remotion/media";
import { staticFile } from "remotion";
import type { Language } from "./copy";
import { MANIFESTS } from "./manifests";

const BASE_VOLUME = 0.42;
const DUCKED_VOLUME = 0.1;
/** Frames spent ramping into and out of a duck. */
const RAMP = 10;

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));

/**
 * Background bed, pulled down under the voiceover and back up between lines.
 * Duck ranges come from the language's own manifest, so the Hebrew cut ducks
 * around its own (longer) takes rather than the English ones.
 */
export const Music: React.FC<{ language: Language }> = ({ language }) => {
  const duckRanges = Object.values(MANIFESTS[language].lines).map((line) => ({
    start: line.startFrame,
    end: line.startFrame + line.frames,
  }));

  return (
    <Audio
      name="Music bed"
      src={staticFile("music/bed.mp3")}
      volume={(frame) => {
        let volume = BASE_VOLUME;

        for (const range of duckRanges) {
          const rampIn = clamp01((frame - (range.start - RAMP)) / RAMP);
          const rampOut = clamp01((range.end + RAMP - frame) / RAMP);
          const amount = Math.min(rampIn, rampOut);
          if (amount <= 0) continue;
          volume = Math.min(
            volume,
            BASE_VOLUME + (DUCKED_VOLUME - BASE_VOLUME) * amount,
          );
        }

        return volume;
      }}
    />
  );
};
