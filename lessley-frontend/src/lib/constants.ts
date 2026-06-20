// Sourced from MongoDB club_list and mcc_list collections.
// Keep in sync with the database when clubs or categories are added.

export const CLUBS = [
  { id: "club_behatsdaa", name: "Behatsdaa" },
  { id: "club_mastercard", name: "Mastercard Israel" },
  { id: "club_topcash", name: "Isracard TopCash" },
  { id: "club_hot", name: "HOT Israel" },
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

export function formatCategoryLabel(value: string): string {
  return value
    .split("_")
    .map((word) => (word.length <= 1 ? word : word.charAt(0) + word.slice(1).toLowerCase()))
    .join(" ")
}
