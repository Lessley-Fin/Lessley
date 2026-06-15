import mockNotifications from "@/data/mockNotifications.json"
import type { AppNotification, AppNotificationWithRead } from "@/features/notifications/notificationTypes"

/** Mock default: only the newest notification starts unread. */
const MOCK_DEFAULT_UNREAD_ID = "n-001"

function createMockDefaultReadIds(): Set<string> {
  const items = mockNotifications as AppNotification[]
  return new Set(items.map((item) => item.id).filter((id) => id !== MOCK_DEFAULT_UNREAD_ID))
}

/** Session read state; resets to mock defaults on full page reload. */
let readNotificationIds = createMockDefaultReadIds()

export function getNotifications(): AppNotificationWithRead[] {
  const items = mockNotifications as AppNotification[]
  return items.map((item) => ({
    ...item,
    read: readNotificationIds.has(item.id),
  }))
}

export function getUnreadCount(): number {
  return getNotifications().filter((n) => !n.read).length
}

export function markAllNotificationsRead() {
  const items = mockNotifications as AppNotification[]
  readNotificationIds = new Set(items.map((item) => item.id))
}
