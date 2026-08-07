// Sourced from MongoDB clubs and mcc_list collections.
// Keep in sync with the database when clubs or categories are added
// (lessley-deals/data/seed/clubs.json is the source of truth).

export const CLUBS = [
  { id: "club_behatsdaa", name: "Behatsdaa" },
  { id: "club_mastercard", name: "Mastercard Israel" },
  { id: "club_topcash", name: "Isracard TopCash" },
  { id: "club_hot", name: "HOT Israel" },
  { id: "club_swish", name: "Swish (נפשונית)" },
  { id: "club_hever_gift_card_company", name: "Hever (חבר) — Gift Cards" },
  { id: "club_hever_teamim_card_store", name: "Hever (חבר) — טעמים" },
  { id: "club_paisplus", name: "PaisPlus" },
  { id: "club_paisplus_food_chains", name: "PaisPlus — Food Chains Cash Card" },
  { id: "club_paisplus_networks", name: "PaisPlus — Networks Cash Card" },
] as const

export const MATCH_LEVELS = ["Low", "Medium", "High"] as const

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
  { label: "1 week", days: 7 },
  { label: "1 month", days: 30 },
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
} as const

export const NOTIFICATION_POLL_INTERVAL_MS = 15_000

export function formatCategoryLabel(value: string): string {
  return value
    .split("_")
    .map((word) => (word.length <= 1 ? word : word.charAt(0) + word.slice(1).toLowerCase()))
    .join(" ")
}
