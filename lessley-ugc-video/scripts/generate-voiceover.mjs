/**
 * Generates the ad voiceover into public/voiceover/<lang>/ and writes a manifest
 * of per-line durations that the composition reads.
 *
 *   node scripts/generate-voiceover.mjs               # both languages
 *   LANG_ONLY=he node scripts/generate-voiceover.mjs  # just Hebrew
 *
 * Engine selection, best first:
 *   ELEVENLABS_API_KEY set -> ElevenLabs
 *   edge-tts importable    -> Microsoft neural voices (default; needs network)
 *   otherwise              -> Windows SAPI (offline, robotic, English only)
 *
 * Force one with VOICE_ENGINE=elevenlabs|edge|sapi. Override voices with
 * EDGE_VOICE / EDGE_VOICE_HE / ELEVENLABS_VOICE_ID / SAPI_VOICE.
 *
 * Note: edge-tts sends the script text to Microsoft's Edge read-aloud endpoint.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { FPS, LINES, TONES } from "./voiceover-lines.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const tmpDir = join(root, "node_modules", ".voiceover-tmp");

const API_KEY = process.env.ELEVENLABS_API_KEY;
const VOICE_ID = process.env.ELEVENLABS_VOICE_ID ?? "21m00Tcm4TlvDq8ikWAM";
const SAPI_VOICE = process.env.SAPI_VOICE ?? "Microsoft Zira Desktop";

const LANGUAGES = {
  en: {
    edgeVoice: process.env.EDGE_VOICE ?? "en-US-AvaMultilingualNeural",
    text: (line) => line.text,
    rate: (line, tone) => line.edgeRate ?? tone.edgeRate,
    startFrame: (line) => line.startFrame,
  },
  he: {
    edgeVoice: process.env.EDGE_VOICE_HE ?? "he-IL-AvriNeural",
    text: (line) => line.he,
    rate: (line, tone) => line.heRate ?? tone.edgeRate,
    startFrame: (line) => line.heStartFrame ?? line.startFrame,
  },
};

// LANG is already set by some shells, so this uses a dedicated name.
const requested = process.env.LANG_ONLY ?? "all";
const targets = requested === "all" ? Object.keys(LANGUAGES) : [requested];

mkdirSync(tmpDir, { recursive: true });

const remotion = (args) =>
  execFileSync("npx", ["remotion", ...args], {
    cwd: root,
    encoding: "utf8",
    shell: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

const xmlEscape = (value) =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

async function synthesizeElevenLabs(text, tone, outPath) {
  const response = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`,
    {
      method: "POST",
      headers: {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json",
        Accept: "audio/mpeg",
      },
      body: JSON.stringify({
        text,
        model_id: "eleven_multilingual_v2",
        voice_settings: {
          stability: tone.stability,
          similarity_boost: 0.75,
          style: tone.style,
        },
      }),
    },
  );

  if (!response.ok) {
    throw new Error(
      `ElevenLabs ${response.status}: ${(await response.text()).slice(0, 300)}`,
    );
  }

  writeFileSync(outPath, Buffer.from(await response.arrayBuffer()));
}

function synthesizeSapi(id, text, tone, outPath) {
  const ssmlPath = join(tmpDir, `${id}.ssml`);
  writeFileSync(
    ssmlPath,
    `<?xml version="1.0" encoding="utf-8"?>
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <prosody pitch="${tone.pitch}">${xmlEscape(text)}</prosody>
</speak>`,
    "utf8",
  );

  const ps = `
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('${SAPI_VOICE}')
$s.Rate = ${tone.sapiRate}
$s.SetOutputToWaveFile('${outPath.replace(/\\/g, "\\\\")}')
$s.SpeakSsml((Get-Content -Raw '${ssmlPath.replace(/\\/g, "\\\\")}'))
$s.Dispose()
`;
  execFileSync("powershell", ["-NoProfile", "-NonInteractive", "-Command", ps], {
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function synthesizeEdge(voice, text, rate, pitch, outPath) {
  execFileSync(
    "python",
    [
      "-m",
      "edge_tts",
      "--voice",
      voice,
      // Equals form is required: a bare "-14%" would be parsed as a flag.
      `--rate=${rate}`,
      `--pitch=${pitch}`,
      "--text",
      text,
      "--write-media",
      outPath,
    ],
    { stdio: ["ignore", "pipe", "pipe"] },
  );
}

function edgeAvailable() {
  try {
    execFileSync("python", ["-c", "import edge_tts"], {
      stdio: ["ignore", "ignore", "ignore"],
    });
    return true;
  } catch {
    return false;
  }
}

const durationOf = (file) =>
  Number(
    remotion([
      "ffprobe",
      "-v",
      "error",
      "-show_entries",
      "format=duration",
      "-of",
      "csv=p=0",
      file,
    ]).trim(),
  );

const pickEngine = () => {
  const forced = process.env.VOICE_ENGINE;
  if (forced) return forced;
  if (API_KEY) return "elevenlabs";
  if (edgeAvailable()) return "edge";
  return "sapi";
};

const engine = pickEngine();
let totalOverruns = 0;

for (const lang of targets) {
  const config = LANGUAGES[lang];
  if (!config) throw new Error(`Unknown language "${lang}"`);
  if (engine === "sapi" && lang !== "en") {
    throw new Error("The SAPI fallback has no Hebrew voice — install edge-tts.");
  }

  const outDir = join(root, "public", "voiceover", lang);
  mkdirSync(outDir, { recursive: true });

  const voice =
    engine === "sapi"
      ? SAPI_VOICE
      : engine === "edge"
        ? config.edgeVoice
        : VOICE_ID;
  console.log(`\n[${lang}] engine: ${engine} (${voice})`);

  const manifest = { engine, language: lang, voice, lines: {} };

  for (const line of LINES) {
    const tone = TONES[line.tone];
    const text = config.text(line);
    if (!text) throw new Error(`Line ${line.id} has no "${lang}" text`);

    const rawPath = join(tmpDir, `${line.id}.raw`);
    const mp3Path = join(outDir, `${line.id}.mp3`);

    if (engine === "elevenlabs") {
      await synthesizeElevenLabs(text, tone, rawPath);
    } else if (engine === "edge") {
      synthesizeEdge(voice, text, config.rate(line, tone), tone.edgePitch, rawPath);
    } else {
      synthesizeSapi(line.id, text, tone, rawPath);
    }

    // Normalize every engine's output to the same mp3 the composition expects.
    remotion([
      "ffmpeg",
      "-y",
      "-i",
      rawPath,
      "-ac",
      "1",
      "-ar",
      "44100",
      // Even out level across takes so no line jumps out of the mix.
      "-af",
      "loudnorm=I=-16:TP=-1.5:LRA=11",
      "-codec:a",
      "libmp3lame",
      "-b:a",
      "128k",
      mp3Path,
    ]);

    const seconds = durationOf(mp3Path);
    const frames = Math.ceil(seconds * FPS);
    // The real constraint is that no two lines talk over each other. A take may
    // tail past its own scene window; it may not reach the next line's start.
    const start = config.startFrame(line);
    const next = LINES[LINES.indexOf(line) + 1];
    const limit = next ? config.startFrame(next) - start : line.windowFrames;
    const fits = frames <= limit;
    if (!fits) totalOverruns++;

    manifest.lines[line.id] = {
      file: `voiceover/${lang}/${line.id}.mp3`,
      seconds: Number(seconds.toFixed(3)),
      frames,
      startFrame: start,
      windowFrames: line.windowFrames,
    };

    console.log(
      `  ${fits ? "ok  " : "OVER"} ${line.id.padEnd(15)} ${seconds.toFixed(2)}s ` +
        `(${frames}/${limit} to next)  ${text.slice(0, 32)}`,
    );
  }

  const manifestPath = join(root, "src", "AppAd", `voiceover-manifest.${lang}.json`);
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(`  manifest -> ${manifestPath}`);
}

rmSync(tmpDir, { recursive: true, force: true });

if (totalOverruns > 0) {
  console.log(
    `\n${totalOverruns} line(s) run into the next line. Shorten the text, raise the rate, or move startFrame.`,
  );
  process.exitCode = 1;
}
