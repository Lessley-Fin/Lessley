export interface NotificationDto {
  id: string
  message: string
  dealId: string | null
  sentAt: string
  type: string
  calcType: string | null
  data: string | null
  isRead: boolean
  readAt: string | null
  categories: string[] | null
}

export interface SignalRNotificationPayload {
  timestamp: string
  message: string
  dealId?: string | null
  calcType?: string | null
  type: string
  group?: string
  categories?: string[]
}
