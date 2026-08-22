import type { ReactNode } from "react";

export type Language = "en" | "he";

export const isRtl = (language: Language) => language === "he";

/**
 * On-screen captions, synced from ad_description.md and ad_description_he.md.
 *
 * Keyed by the line ids in voiceover-lines.mjs, except "06a"/"06b": the insights
 * sentence is too long for one caption card, so it is split across two while the
 * voiceover stays a single take.
 *
 * The captions keep the brand the way each script writes it — "Lessley" in the
 * English cut, לסלי in the Hebrew one. The Hebrew *voice* track spells it
 * לֶס לִי so the engine pronounces it correctly; that spelling never appears
 * on screen.
 */
export const CAPTIONS: Record<Language, Record<string, ReactNode>> = {
  en: {
    "02-meet": <>Meet Lessley — your financial autopilot.</>,
    "03a-assume": (
      <>Assume you&apos;re about to purchase in a store — but don&apos;t know which card to use.</>
    ),
    "03b-calculates": (
      <>
        Lessley finds real-time deals based on your loyalty clubs, and
        calculates the best price{" "}
        <span style={{ color: "#6FBDC4" }}>FOR YOU!</span>
      </>
    ),
    "04-hot": <>Lessley suggests you hot deals, based on your profile.</>,
    "05-banking": (
      <>
        Connect once with Open-Banking. Your bank syncs securely — with read
        only permissions.
      </>
    ),
    "06a-insights": (
      <>
        Lessley analyzes your profile and learns your actual spending habits
        based on your expenses,
      </>
    ),
    "06b-insights": <>and creates insights for your daily routine.</>,
    "07a-use": (
      <>Use Lessley recommendations and stop leaving money on the table.</>
    ),
    "07b-power": <>Start to maximize your purchasing power.</>,
  },
  he: {
    "02-meet": <>תכירו את לסלי — העוזרת הפיננסית האישית שלכם</>,
    "03a-assume": (
      <>תדמיינו שאתם נמצאים בחנות ואתם לא יודעים באיזה כרטיס להשתמש...</>
    ),
    "03b-calculates": (
      <>
        לסלי מוצאת בזמן אמת דילים לפי הכרטיסים וחברי המועדון שלכם, ומחשבת את
        המחיר הטוב ביותר{" "}
        <span style={{ color: "#6FBDC4" }}>בשבילכם!</span>
      </>
    ),
    "04-hot": <>לסלי מציעה לכם דילים חמים, לפי הפרופיל שלכם</>,
    "05-banking": (
      <>
        התחברות חד פעמית לבנקאות פתוחה. הבנק שלכם מתחבר בצורה מאובטחת — עם
        הרשאות קריאה בלבד
      </>
    ),
    // Split later than the English one: Hebrew sets wider here and a fourth
    // line would crowd the phone.
    "06a-insights": (
      <>לסלי מנתחת את הפרופיל שלכם ולומדת את הרגלי הצריכה האמיתית שלכם</>
    ),
    "06b-insights": (
      <>בהתבסס על הקניות שאתם עושים, ומייצרת לכם תובנות מחיי היום-יום</>
    ),
    "07a-use": (
      <>תשתמשו בהמלצות שלסלי מספקת ותפסיקו להפסיד כסף על הקניות שלכם</>
    ),
    "07b-power": <>תתחילו להגדיל את כוח הקנייה שלכם</>,
  },
};

/** Scene 1 headline, with the payoff half in brand teal. */
export const HOOK_LINE: Record<Language, ReactNode> = {
  en: (
    <>
      Tired of missing out on{" "}
      <span style={{ color: "#6FBDC4" }}>club discounts?</span>
    </>
  ),
  he: (
    <>
      מבולבלים ונמאס לכם{" "}
      <span style={{ color: "#6FBDC4" }}>לפספס הנחות?</span>
    </>
  ),
};

/** The savings drifting past behind the hook. */
export const MISSED_LABELS: Record<Language, string[]> = {
  en: [
    "−₪18.40 missed",
    "−₪7.90 missed",
    "−₪32.10 missed",
    "−₪12.60 missed",
  ],
  he: [
    "−₪18.40 פוספסו",
    "−₪7.90 פוספסו",
    "−₪32.10 פוספסו",
    "−₪12.60 פוספסו",
  ],
};

/** Scene 8 sign-off. */
export const CTA_LINE: Record<Language, ReactNode> = {
  en: (
    <>
      Lessley —<br />
      <span style={{ color: "#6FBDC4" }}>Your Financial Waze.</span>
    </>
  ),
  // No em dash here: at the start of an RTL line it renders to the left of the
  // wordmark, which reads as "— לסלי" to anyone scanning left to right.
  he: (
    <>
      לסלי
      <br />
      <span style={{ color: "#6FBDC4" }}>הווייז הפיננסי שלכם</span>
    </>
  ),
};
