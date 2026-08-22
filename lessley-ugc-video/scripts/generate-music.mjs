/**
 * Synthesizes the ad's background music bed into public/music/bed.mp3.
 *
 *   node scripts/generate-music.mjs
 *
 * The track is generated from scratch — soft pad, gentle bell arpeggio, sub
 * root, light Schroeder reverb — so the ad carries no third-party music
 * licence. Level is deliberately conservative; the final mix level and the
 * voiceover ducking live in src/AppAd/Music.tsx.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const outDir = join(root, "public", "music");
const tmpWav = join(root, "node_modules", ".music-bed.wav");

const SR = 44100;
const SECONDS = 59;
const N = SR * SECONDS;

// A major, the optimistic end of the app's teal palette.
const CHORDS = [
  [57, 61, 64, 69], // A
  [54, 57, 61, 66], // F#m
  [50, 54, 57, 62], // D
  [52, 56, 59, 64], // E
  [57, 61, 64, 69], // A
  [54, 57, 61, 66], // F#m
  [47, 50, 54, 59], // Bm
  [52, 56, 59, 64], // E
];
const CHORD_SECONDS = SECONDS / CHORDS.length;

const freq = (midi) => 440 * 2 ** ((midi - 69) / 12);

const left = new Float64Array(N);
const right = new Float64Array(N);

/** Slow swell in, long tail out, so chords bleed into each other. */
const padEnvelope = (t, duration) => {
  const attack = 1.6;
  const release = 2.4;
  if (t < 0 || t > duration) return 0;
  if (t < attack) return 0.5 - 0.5 * Math.cos((Math.PI * t) / attack);
  if (t > duration - release) {
    const x = (duration - t) / release;
    return 0.5 - 0.5 * Math.cos(Math.PI * x);
  }
  return 1;
};

const addPartial = (startSample, lengthSamples, hz, amp, duration, detune) => {
  for (let i = 0; i < lengthSamples; i++) {
    const s = startSample + i;
    if (s < 0 || s >= N) continue;
    const t = i / SR;
    const env = padEnvelope(t, duration);
    if (env <= 0) continue;
    // A touch of drift keeps the pad from sounding like a static oscillator.
    const drift = 1 + 0.0016 * Math.sin(2 * Math.PI * 0.07 * t);
    left[s] += amp * env * Math.sin(2 * Math.PI * hz * (1 - detune) * drift * t);
    right[s] += amp * env * Math.sin(2 * Math.PI * hz * (1 + detune) * drift * t);
  }
};

// --- Pad + sub -------------------------------------------------------------
CHORDS.forEach((chord, index) => {
  const startSample = Math.floor(index * CHORD_SECONDS * SR);
  const duration = CHORD_SECONDS + 2.0; // overlap into the next chord
  const lengthSamples = Math.floor(duration * SR);

  chord.forEach((midi, voice) => {
    const base = freq(midi);
    const weight = voice === 0 ? 0.9 : 0.7;
    addPartial(startSample, lengthSamples, base, 0.115 * weight, duration, 0.0022);
    addPartial(startSample, lengthSamples, base * 2, 0.038 * weight, duration, 0.0016);
    addPartial(startSample, lengthSamples, base * 3, 0.014 * weight, duration, 0.001);
  });

  // Sub root, one octave below the chord root.
  addPartial(startSample, lengthSamples, freq(chord[0] - 12), 0.1, duration, 0.0004);
});

// --- Bell arpeggio ---------------------------------------------------------
const STEP = CHORD_SECONDS / 8;
const PATTERN = [0, 2, 1, 3, 2, 1, 3, 2];

CHORDS.forEach((chord, chordIndex) => {
  PATTERN.forEach((voice, step) => {
    const startSample = Math.floor(
      (chordIndex * CHORD_SECONDS + step * STEP) * SR,
    );
    // Lift every other phrase an octave so the line breathes.
    const midi = chord[voice] + (step % 4 === 0 ? 12 : 0);
    const hz = freq(midi);
    const decay = 1.5;
    const lengthSamples = Math.floor(decay * SR);

    for (let i = 0; i < lengthSamples; i++) {
      const s = startSample + i;
      if (s < 0 || s >= N) continue;
      const t = i / SR;
      const env = Math.exp(-t * 3.1) * (1 - Math.exp(-t * 260));
      const amp = 0.05 * env;
      left[s] += amp * Math.sin(2 * Math.PI * hz * t);
      right[s] += amp * Math.sin(2 * Math.PI * hz * 1.001 * t);
      // Faint second partial gives it the bell edge.
      left[s] += amp * 0.3 * Math.sin(2 * Math.PI * hz * 2.01 * t);
      right[s] += amp * 0.3 * Math.sin(2 * Math.PI * hz * 2.005 * t);
    }
  });
});

// --- Reverb (4 parallel combs into 2 series allpasses) ---------------------
const comb = (input, delayMs, feedback) => {
  const d = Math.floor((delayMs / 1000) * SR);
  const out = new Float64Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const delayed = i >= d ? out[i - d] : 0;
    out[i] = input[i] + delayed * feedback;
  }
  return out;
};

const allpass = (input, delayMs, gain) => {
  const d = Math.floor((delayMs / 1000) * SR);
  const out = new Float64Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const delayedIn = i >= d ? input[i - d] : 0;
    const delayedOut = i >= d ? out[i - d] : 0;
    out[i] = -gain * input[i] + delayedIn + gain * delayedOut;
  }
  return out;
};

const reverb = (channel, spread) => {
  const combs = [
    comb(channel, 29.7 + spread, 0.78),
    comb(channel, 37.1 + spread, 0.76),
    comb(channel, 41.1 + spread, 0.74),
    comb(channel, 43.7 + spread, 0.72),
  ];
  const summed = new Float64Array(channel.length);
  for (let i = 0; i < channel.length; i++) {
    summed[i] = (combs[0][i] + combs[1][i] + combs[2][i] + combs[3][i]) / 4;
  }
  return allpass(allpass(summed, 5.0, 0.7), 1.7, 0.7);
};

const wetL = reverb(left, 0);
const wetR = reverb(right, 1.3);
const WET = 0.32;

for (let i = 0; i < N; i++) {
  left[i] = left[i] * (1 - WET) + wetL[i] * WET;
  right[i] = right[i] * (1 - WET) + wetR[i] * WET;
}

// --- Global fades + peak normalize ----------------------------------------
const fadeIn = 2.5 * SR;
const fadeOut = 3.5 * SR;
for (let i = 0; i < N; i++) {
  let g = 1;
  if (i < fadeIn) g *= 0.5 - 0.5 * Math.cos((Math.PI * i) / fadeIn);
  if (i > N - fadeOut) {
    const x = (N - i) / fadeOut;
    g *= 0.5 - 0.5 * Math.cos(Math.PI * x);
  }
  left[i] *= g;
  right[i] *= g;
}

let peak = 0;
for (let i = 0; i < N; i++) {
  peak = Math.max(peak, Math.abs(left[i]), Math.abs(right[i]));
}
const gain = peak > 0 ? 0.78 / peak : 1;

// --- Write 16-bit stereo WAV ----------------------------------------------
const dataBytes = N * 2 * 2;
const buffer = Buffer.alloc(44 + dataBytes);
buffer.write("RIFF", 0, "ascii");
buffer.writeUInt32LE(36 + dataBytes, 4);
buffer.write("WAVE", 8, "ascii");
buffer.write("fmt ", 12, "ascii");
buffer.writeUInt32LE(16, 16);
buffer.writeUInt16LE(1, 20);
buffer.writeUInt16LE(2, 22);
buffer.writeUInt32LE(SR, 24);
buffer.writeUInt32LE(SR * 2 * 2, 28);
buffer.writeUInt16LE(4, 32);
buffer.writeUInt16LE(16, 34);
buffer.write("data", 36, "ascii");
buffer.writeUInt32LE(dataBytes, 40);

const clamp = (v) => Math.max(-32768, Math.min(32767, Math.round(v * 32767)));
for (let i = 0; i < N; i++) {
  buffer.writeInt16LE(clamp(left[i] * gain), 44 + i * 4);
  buffer.writeInt16LE(clamp(right[i] * gain), 44 + i * 4 + 2);
}

mkdirSync(outDir, { recursive: true });
writeFileSync(tmpWav, buffer);

execFileSync(
  "npx",
  [
    "remotion",
    "ffmpeg",
    "-y",
    "-i",
    tmpWav,
    "-af",
    "loudnorm=I=-20:TP=-2:LRA=11",
    "-codec:a",
    "libmp3lame",
    "-b:a",
    "160k",
    join(outDir, "bed.mp3"),
  ],
  { cwd: root, shell: true, stdio: ["ignore", "pipe", "pipe"] },
);

console.log(`Wrote ${join(outDir, "bed.mp3")} (${SECONDS}s, generated)`);
