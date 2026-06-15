export type NotificationCategory =
  | "missed_savings"
  | "hot_deal"
  | "monthly_report"
  | "club_match"
  | "spending_insight"
  | "bank_sync"
  | "welcome"

/** Matches SendNotificationDto schema: message, time, category, deal_id */
export interface AppNotification {
  id: string
  message: string
  time: string
  category: NotificationCategory
  deal_id: string
}

export interface AppNotificationWithRead extends AppNotification {
  read: boolean
}

export const NOTIFICATION_CATEGORY_LABELS: Record<NotificationCategory, string> = {
  missed_savings: "Missed savings",
  hot_deal: "Hot deal",
  monthly_report: "Monthly report",
  club_match: "Club match",
  spending_insight: "Spending insight",
  bank_sync: "Bank sync",
  welcome: "Welcome",
}
