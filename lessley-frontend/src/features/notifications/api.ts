import { apiFetch } from "@/lib/api-client"
import type { NotificationDto } from "./notificationTypes"

export async function fetchNotifications(): Promise<NotificationDto[]> {
  const data = await apiFetch<NotificationDto[] | null>("/api/Notification")
  return Array.isArray(data) ? data : []
}

export async function markNotificationRead(notificationId: string): Promise<void> {
  await apiFetch(`/api/Notification/${notificationId}/read`, { method: "POST" })
}

