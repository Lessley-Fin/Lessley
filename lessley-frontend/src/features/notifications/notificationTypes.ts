export interface NotificationDto {
  id: string
  message: string
  dealId: string | null
  sentAt: string
  targetType: "user" | "group"
  isRead: boolean
  readAt: string | null
}

export interface SignalRNotificationPayload {
  timestamp: string
  message: string
  dealId: string | null
  type: "user" | "group"
  group?: string
}
