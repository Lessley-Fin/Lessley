import { useCallback, useEffect, useRef, useState } from "react"
import {
  HubConnectionBuilder,
  HubConnectionState,
  LogLevel,
  type HubConnection,
} from "@microsoft/signalr"
import type { NotificationDto, SignalRNotificationPayload } from "./notificationTypes"
import { API_GATEWAY_URL } from "@/lib/api"
import { getValidAccessToken } from "@/lib/auth"

interface UseNotificationsOptions {
  email: string
  enabled: boolean
}

export function useNotifications({ email, enabled }: UseNotificationsOptions) {
  const [notifications, setNotifications] = useState<NotificationDto[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const connectionRef = useRef<HubConnection | null>(null)

  const unreadCount = notifications.filter((n) => !n.isRead).length

  const fetchNotifications = useCallback(async () => {
    if (!email) return
    setIsLoading(true)
    try {
      const token = await getValidAccessToken()
      if (!token) return

      const response = await fetch(
        `${API_GATEWAY_URL}/api/Notification/user/${encodeURIComponent(email)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )

      if (!response.ok) return

      const data = (await response.json()) as NotificationDto[]
      setNotifications(Array.isArray(data) ? data : [])
    } catch {
      // Keep current state on fetch failure
    } finally {
      setIsLoading(false)
    }
  }, [email])

  const markAllRead = useCallback(async () => {
    if (!email) return
    try {
      const token = await getValidAccessToken()
      if (!token) return

      const response = await fetch(
        `${API_GATEWAY_URL}/api/Notification/read/${encodeURIComponent(email)}`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      )

      if (response.ok) {
        setNotifications((prev) =>
          prev.map((n) => (n.isRead ? n : { ...n, isRead: true, readAt: new Date().toISOString() }))
        )
      }
    } catch {
      // Silent failure
    }
  }, [email])

  const markOneRead = useCallback(
    async (notificationId: string) => {
      if (!email) return
      try {
        const token = await getValidAccessToken()
        if (!token) return

        const response = await fetch(
          `${API_GATEWAY_URL}/api/Notification/${notificationId}/read/${encodeURIComponent(email)}`,
          { method: "POST", headers: { Authorization: `Bearer ${token}` } }
        )

        if (response.ok) {
          setNotifications((prev) =>
            prev.map((n) =>
              n.id === notificationId ? { ...n, isRead: true, readAt: new Date().toISOString() } : n
            )
          )
        }
      } catch {
        // Silent failure
      }
    },
    [email]
  )

  const handleIncoming = useCallback((payload: SignalRNotificationPayload) => {
    const newNotification: NotificationDto = {
      id: crypto.randomUUID(),
      message: payload.message,
      dealId: payload.dealId,
      sentAt: payload.timestamp,
      targetType: payload.type,
      isRead: false,
      readAt: null,
    }
    setNotifications((prev) => [newNotification, ...prev])
  }, [])

  useEffect(() => {
    if (!enabled || !email) return

    void fetchNotifications()

    const connection = new HubConnectionBuilder()
      .withUrl(`${API_GATEWAY_URL}/hubs/notifications`, {
        accessTokenFactory: () => getValidAccessToken().then((t) => t ?? ""),
      })
      .withAutomaticReconnect([0, 2000, 5000, 10000, 30000])
      .configureLogging(LogLevel.Warning)
      .build()

    connectionRef.current = connection

    connection.on("DealUserNotification", handleIncoming)
    connection.on("DealGroupNotification", handleIncoming)

    connection.onreconnected(() => {
      setIsConnected(true)
      void fetchNotifications()
    })
    connection.onreconnecting(() => setIsConnected(false))
    connection.onclose(() => setIsConnected(false))

    void connection.start().then(() => setIsConnected(true)).catch(() => setIsConnected(false))

    return () => {
      connection.off("DealUserNotification")
      connection.off("DealGroupNotification")
      if (connection.state !== HubConnectionState.Disconnected) {
        void connection.stop()
      }
      connectionRef.current = null
      setIsConnected(false)
    }
  }, [enabled, email, fetchNotifications, handleIncoming])

  return {
    notifications,
    unreadCount,
    isConnected,
    isLoading,
    markAllRead,
    markOneRead,
    refetch: fetchNotifications,
  }
}
