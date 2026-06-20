import { useEffect } from "react"
import {
  HubConnectionBuilder,
  HubConnectionState,
  LogLevel,
} from "@microsoft/signalr"
import { useQueryClient } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
import { API_GATEWAY_URL } from "@/lib/api-client"
import { getValidAccessToken } from "@/lib/auth"
import { queryKeys } from "@/lib/query-keys"
import type { NotificationDto, SignalRNotificationPayload } from "./notificationTypes"

export function useSignalR() {
  const queryClient = useQueryClient()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  useEffect(() => {
    if (!isAuthenticated) return

    const connection = new HubConnectionBuilder()
      .withUrl(`${API_GATEWAY_URL}/hubs/notifications`, {
        accessTokenFactory: () =>
          getValidAccessToken().then((t) => t ?? ""),
      })
      .withAutomaticReconnect([0, 2000, 5000, 10000, 30000])
      .configureLogging(LogLevel.Warning)
      .build()

    const handleIncoming = (payload: SignalRNotificationPayload) => {
      const newNotification: NotificationDto = {
        id: crypto.randomUUID(),
        message: payload.message,
        dealId: payload.dealId ?? null,
        sentAt: payload.timestamp,
        type: payload.type,
        calcType: null,
        data: null,
        isRead: false,
        readAt: null,
        categories: null,
      }
      queryClient.setQueryData<NotificationDto[]>(
        queryKeys.notifications.list(),
        (old) => [newNotification, ...(old ?? [])],
      )
    }

    connection.on("DealUserNotification", handleIncoming)
    connection.on("DealGroupNotification", handleIncoming)
    connection.on("CalcNotification", handleIncoming)

    connection.onreconnected(() => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.all,
      })
    })
    connection.onreconnecting(() => {})
    connection.onclose(() => {})

    void connection.start()

    return () => {
      connection.off("DealUserNotification")
      connection.off("DealGroupNotification")
      connection.off("CalcNotification")
      if (connection.state !== HubConnectionState.Disconnected) {
        void connection.stop()
      }
    }
  }, [isAuthenticated, queryClient])
}
