export const MATCH_LEVELS = ["Low", "Medium", "High"] as const

export const MATCH_LEVEL_OPTIONS = [
  { value: "Low", label: "Broad (top 75%)" },
  { value: "Medium", label: "Medium (top 50%)" },
  { value: "High", label: "Strict (top 25%)" },
] as const

export const MCC_CATEGORIES = [
  "ALCOHOL_&_TOBACCO",
  "BARS",
  "BEAUTY",
  "BOOKS_&_GAMES",
  "BUSINESS_EXPENSES",
  "CAPITAL_MARKET",
  "CAR_&_FUEL",
  "CHARITY",
  "CLOTHES_&_ACCESSORIES",
  "COFFEE_&_SNACKS",
  "COMMUNICATIONS",
  "CULTURE_&_EVENTS",
  "EDUCATION",
  "ELECTRONICS",
  "FEES",
  "FINANCE_OTHER",
  "FLIGHTS",
  "FOOD_&_DRINKS_OTHER",
  "FURNITURE_&_INTERIOR",
  "GARDEN",
  "GIFTS",
  "GROCERIES",
  "HEALTHCARE",
  "HEALTH_&_BEAUTY_OTHER",
  "HOBBIES",
  "HOBBY_&_SPORTS_EQUIPMENT",
  "HOME",
  "HOME_IMPROVEMENTS_OTHER",
  "HOUSEHOLD_&_SERVICES_-_OTHER",
  "INSURANCE_&_FEES",
  "KIDS",
  "LEISURE_OTHER",
  "LOANS",
  "OTHER",
  "PETS",
  "PHARMACY",
  "PUBLIC_TRANSPORT",
  "RENOVATION_&_REPAIRS",
  "RESTAURANT",
  "SAVINGS",
  "SERVICES",
  "SHOPPING_OTHER",
  "SPORTS_&_FITNESS",
  "TRANSPORT_OTHER",
  "UTILITIES",
  "VACATION",
] as const

export const TIME_RANGE_OPTIONS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
  { label: "1 year", days: 365 },
] as const

export const INSIGHTS_DEFAULTS = {
  TOP_STORES_LIMIT: 3,
  TOP_CATEGORIES_LIMIT: 3,
  MORE_CATEGORIES_OFFSET: 1,
  MORE_CATEGORIES_LIMIT: 4,
  ACCOUNT_HIGHLIGHTS_LIMIT: 3,
  RECENT_TRANSACTIONS_LIMIT: 5,
  TOP_CLUB_RECOMMENDATIONS_LIMIT: 3,
  DEFAULT_TIME_RANGE_DAYS: 90,
  CAROUSEL_LIST_LIMIT: 10,
  CAROUSEL_CATEGORY_LIMIT: 6,
} as const

export function formatCategoryLabel(value: string): string {
  return value
    .split("_")
    .map((word) => (word.length <= 1 ? word : word.charAt(0) + word.slice(1).toLowerCase()))
    .join(" ")
}

// Purely decorative — the backend has no per-deal/per-store image, so this gives deal cards a
// visual anchor keyed off the known, fixed MCC category vocabulary rather than guessing from
// free-text store names.
const CATEGORY_EMOJI: Record<string, string> = {
  "ALCOHOL_&_TOBACCO": "🍷",
  BARS: "🍸",
  BEAUTY: "💄",
  "BOOKS_&_GAMES": "📚",
  BUSINESS_EXPENSES: "💼",
  CAPITAL_MARKET: "📈",
  "CAR_&_FUEL": "⛽",
  CHARITY: "🤝",
  "CLOTHES_&_ACCESSORIES": "👗",
  "COFFEE_&_SNACKS": "☕",
  COMMUNICATIONS: "📱",
  "CULTURE_&_EVENTS": "🎭",
  EDUCATION: "🎓",
  ELECTRONICS: "🔌",
  FEES: "💳",
  FINANCE_OTHER: "💰",
  FLIGHTS: "✈️",
  "FOOD_&_DRINKS_OTHER": "🍽️",
  "FURNITURE_&_INTERIOR": "🛋️",
  GARDEN: "🌿",
  GIFTS: "🎁",
  GROCERIES: "🛒",
  HEALTHCARE: "🏥",
  "HEALTH_&_BEAUTY_OTHER": "💊",
  HOBBIES: "🎨",
  "HOBBY_&_SPORTS_EQUIPMENT": "🏸",
  HOME: "🏠",
  HOME_IMPROVEMENTS_OTHER: "🔨",
  "HOUSEHOLD_&_SERVICES_-_OTHER": "🧹",
  "INSURANCE_&_FEES": "🛡️",
  KIDS: "🧸",
  LEISURE_OTHER: "🎡",
  LOANS: "🏦",
  OTHER: "🏷️",
  PETS: "🐾",
  PHARMACY: "💊",
  PUBLIC_TRANSPORT: "🚌",
  "RENOVATION_&_REPAIRS": "🔧",
  RESTAURANT: "🍽️",
  SAVINGS: "💰",
  SERVICES: "🧰",
  SHOPPING_OTHER: "🛍️",
  "SPORTS_&_FITNESS": "🏋️",
  TRANSPORT_OTHER: "🚗",
  UTILITIES: "💡",
  VACATION: "🏖️",
}

export function emojiForCategory(category: string | undefined): string {
  if (!category) return "🏷️"
  return CATEGORY_EMOJI[category] ?? "🏷️"
}

// The insights endpoints return a free-text "main - sub" category label (e.g. "FOOD_&_DRINKS -
// GROCERIES"), not a clean MCC_CATEGORIES value, so fall back to a substring match against the
// known vocabulary before giving up on an emoji.
export function emojiForCategoryLabel(category: string | undefined): string {
  if (!category) return "🏷️"
  if (CATEGORY_EMOJI[category]) return CATEGORY_EMOJI[category]
  const upper = category.toUpperCase()
  const match = MCC_CATEGORIES.find((key) => upper.includes(key))
  return match ? CATEGORY_EMOJI[match] : "🏷️"
}

// Backend club/store data has no emoji field — best-effort keyword match onto the name so cards
// still get a visual, falling back to a generic icon when nothing matches.
const CLUB_EMOJI_KEYWORDS: [string, string][] = [
  ["card", "💳"],
  ["bank", "🏦"],
  ["coffee", "☕"],
  ["cafe", "☕"],
  ["grocer", "🛒"],
  ["super", "🛒"],
  ["fuel", "⛽"],
  ["gas", "⛽"],
  ["fashion", "👗"],
  ["cloth", "👗"],
  ["book", "📚"],
  ["game", "🎮"],
  ["pharm", "💊"],
  ["health", "💊"],
  ["restaurant", "🍽️"],
  ["food", "🍽️"],
  ["travel", "✈️"],
  ["flight", "✈️"],
  ["home", "🏠"],
  ["furniture", "🛋️"],
  ["electronic", "🔌"],
  ["beauty", "💄"],
]

export function emojiForClub(name: string): string {
  const lower = name.toLowerCase()
  const match = CLUB_EMOJI_KEYWORDS.find(([keyword]) => lower.includes(keyword))
  return match?.[1] ?? "🎟️"
}

export function emojiForStore(name: string): string {
  const lower = name.toLowerCase()
  const match = CLUB_EMOJI_KEYWORDS.find(([keyword]) => lower.includes(keyword))
  return match?.[1] ?? "🏬"
}
