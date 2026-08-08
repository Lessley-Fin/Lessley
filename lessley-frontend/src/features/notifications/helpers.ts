import type { NotificationDto } from "./notificationTypes"

// Real backend types are "user" | "group" | "deal" | "calc" (with calc split into
// "missed-savings" / "matching-clubs" via calcType) — map those onto the four badge
// categories the design uses, rather than inventing a fifth bucket we can't back with data.
export function notificationBadge(item: NotificationDto): "Analysis" | "Clubs" | "Deal" | "System" {
  if (item.type === "deal") return "Deal"
  if (item.type === "calc") return item.calcType === "matching-clubs" ? "Clubs" : "Analysis"
  return "System"
}

export function notificationTitleKey(item: NotificationDto): "dealMatch" | "clubMatch" | "analysisReady" | "systemUpdate" {
  switch (notificationBadge(item)) {
    case "Deal":
      return "dealMatch"
    case "Clubs":
      return "clubMatch"
    case "Analysis":
      return "analysisReady"
    default:
      return "systemUpdate"
  }
}

export function notificationHasDetail(item: NotificationDto): boolean {
  return Boolean(item.calcType) || Boolean(item.dealId) || Boolean(item.categories && item.categories.length > 0)
}
