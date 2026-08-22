/**
 * The ad's spoken script, synced from ad_description.md and ad_description_he.md.
 *
 * `text` / `he` are the TTS-facing wording and differ slightly from the on-screen
 * captions on purpose:
 *   - engines read punctuation literally, so em dashes become commas
 *   - "Lessley" is spelled לֶס לִי for the Hebrew engine (plain לסלי reads
 *     "Lessaly"); the caption keeps the way the script writes it
 *   - Waze is spelled ווייז so the Hebrew voice says the app name
 *
 * `startFrame` / `windowFrames` mirror the caption Sequences in AppAd.tsx and
 * AppWalkthrough.tsx at 30fps. The generator warns if a take runs into the next.
 * `heStartFrame` lets one language breathe longer without moving the other.
 *
 * Scene map (59s / 1770 frames):
 *   0:00-0:04 hook      0:04-0:08 login        0:08-0:22 optimizer
 *   0:22-0:26 hot deals 0:26-0:32 open banking 0:32-0:45 insights
 *   0:45-0:55 recommendations                  0:55-0:59 CTA
 */
export const FPS = 30;

export const LINES = [
  {
    id: "01-hook",
    tone: "curious",
    text: "Tired of missing out on club discounts?",
    he: "מבולבלים ונמאס לכם לפספס הנחות?",
    startFrame: 0,
    windowFrames: 120,
  },
  {
    id: "02-meet",
    tone: "cheerful",
    text: "Meet Lessley, your financial autopilot.",
    he: "תכירו את לֶס לִי, העוזרת הפיננסית האישית שלכם.",
    startFrame: 120,
    windowFrames: 120,
  },
  {
    id: "03a-assume",
    tone: "excited",
    text: "Assume you're about to purchase in a store, but don't know which card to use.",
    he: "תדמיינו שאתם נמצאים בחנות ואתם לא יודעים באיזה כרטיס להשתמש...",
    // Caption appears on the 0:08 cut; the voice comes in a beat later so it
    // does not talk over the tail of the previous line.
    startFrame: 246,
    heStartFrame: 252,
    windowFrames: 150,
  },
  {
    id: "03b-calculates",
    tone: "excited",
    text: "Lessley finds real-time deals based on your loyalty clubs, and calculates the best price for you!",
    he: "לֶס לִי מוצאת בזמן אמת דילים לפי הכרטיסים וחברי המועדון שלכם, ומחשבת את המחיר הטוב ביותר בשבילכם!",
    startFrame: 400,
    heStartFrame: 410,
    windowFrames: 260,
  },
  {
    id: "04-hot",
    tone: "excited",
    text: "Lessley suggests you hot deals, based on your profile.",
    he: "לֶס לִי מציעה לכם דילים חמים, לפי הפרופיל שלכם.",
    startFrame: 664,
    windowFrames: 120,
  },
  {
    id: "05-banking",
    tone: "excited",
    heStartFrame: 796,
    text: "Connect once with Open Banking. Your bank syncs securely, with read only permissions.",
    he: "התחברות חד פעמית לבנקאות פתוחה. הבנק שלכם מתחבר בצורה מאובטחת, עם הרשאות קריאה בלבד.",
    startFrame: 786,
    windowFrames: 180,
  },
  {
    id: "06-insights",
    tone: "excited",
    heStartFrame: 1044,
    text: "Lessley analyzes your profile and learns your actual spending habits based on your expenses, and creates insights for your daily routine.",
    he: "לֶס לִי מנתחת את הפרופיל שלכם ולומדת את הרגלי הצריכה האמיתית שלכם בהתבסס על הקניות שאתם עושים, ומייצרת לכם תובנות מחיי היום-יום.",
    startFrame: 966,
    windowFrames: 390,
  },
  {
    id: "07a-use",
    tone: "cheerful",
    text: "Use Lessley recommendations and stop leaving money on the table.",
    he: "תשתמשו בהמלצות של לֶס לִי ותפסיקו להפסיד כסף על הקניות שלכם.",
    startFrame: 1356,
    windowFrames: 180,
  },
  {
    id: "07b-power",
    tone: "cheerful",
    text: "Start to maximize your purchasing power.",
    he: "תתחילו להגדיל את כוח הקנייה שלכם.",
    startFrame: 1536,
    windowFrames: 120,
  },
  {
    id: "08-cta",
    tone: "cheerful",
    text: "Lessley. Your Financial Waze.",
    he: "לֶס לִי. הווייז הפיננסי שלכם.",
    startFrame: 1656,
    windowFrames: 120,
  },
];

/**
 * Per-tone delivery, applied by whichever engine is generating.
 * `edge*` drives edge-tts, `sapi*`/`pitch` drive Windows SAPI, and
 * `stability`/`style` drive ElevenLabs.
 */
export const TONES = {
  curious: {
    edgeRate: "+2%",
    edgePitch: "+5Hz",
    sapiRate: 0,
    pitch: "+4%",
    stability: 0.5,
    style: 0.35,
  },
  cheerful: {
    edgeRate: "+7%",
    edgePitch: "+3Hz",
    sapiRate: 1,
    pitch: "+6%",
    stability: 0.45,
    style: 0.45,
  },
  excited: {
    edgeRate: "+13%",
    edgePitch: "+8Hz",
    sapiRate: 2,
    pitch: "+10%",
    stability: 0.35,
    style: 0.6,
  },
};
