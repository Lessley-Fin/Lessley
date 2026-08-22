import { Audio } from "@remotion/media";
import { staticFile } from "remotion";
import type { Language } from "./copy";
import { MANIFESTS } from "./manifests";

/**
 * Every spoken line, placed on one top-level track from the generated manifest.
 *
 * Deliberately not nested inside the caption <Sequence>s: a take is allowed to
 * tail past its own scene cut (that reads as natural delivery), and a Sequence
 * would clip it mid-word. The generator guarantees no take reaches the next
 * one's start, so nothing ever overlaps.
 *
 * Regenerate with: node scripts/generate-voiceover.mjs
 */
export const VoiceoverTrack: React.FC<{ language: Language }> = ({
  language,
}) => {
  return (
    <>
      {Object.entries(MANIFESTS[language].lines).map(([id, line]) => (
        <Audio
          key={id}
          name={`VO ${id}`}
          src={staticFile(line.file)}
          from={line.startFrame}
          durationInFrames={line.frames}
        />
      ))}
    </>
  );
};
