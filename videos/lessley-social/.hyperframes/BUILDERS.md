# The frame builders (`fb.py` + `b1..b7.py`)

**The deliverable is `compositions/frames/*.html`.** That is what `lint`, `check`, the
assembler and the renderer read, and it is the artifact the HyperFrames frame contract
defines. These scripts are the generators that produced those files.

They exist because 13 frames authored by hand drift apart — nine different headline sizes,
nine slightly different entrance timings. Everything shared (the font faces, the design
tokens, the type ramp, the headline bands, and the GSAP helpers that reproduce each motion
rule) lives once in `fb.py`, so the frames read as one film rather than thirteen.

## The trap

`python3 .hyperframes/bN.py` **overwrites its frames wholesale.** A hand edit made directly
in `compositions/frames/*.html` is lost the next time a builder runs.

So: change a frame by editing its builder and re-running, not by editing the HTML — unless
you are deliberately retiring the builders, in which case delete them so nothing can
clobber the HTML later.

## Regenerating

```bash
cd videos/lessley-social
for b in b1 b2 b3 b4 b5 b6 b7; do python3 .hyperframes/$b.py; done
```

Then re-apply the frame-root durations, reassemble and re-inject transitions — the root
`data-duration` is added after generation because the transition injector needs it to
extend each frame's tail across its overlap:

```bash
S=~/.claude/skills/product-launch-video
node $S/scripts/assemble-index.mjs --storyboard ./STORYBOARD.md --hyperframes .
node $S/scripts/transitions.mjs inject --storyboard ./STORYBOARD.md --hyperframes .
npx hyperframes check
```
