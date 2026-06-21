import { createElement, useEffect } from "react"
import {
  HubConnectionBuilder,
  HubConnectionState,
  LogLevel,
} from "@microsoft/signalr"
import { useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { useAuthStore } from "@/features/auth/store"
import { API_GATEWAY_URL } from "@/lib/api-client"
import { getValidAccessToken } from "@/lib/auth"
import { queryKeys } from "@/lib/query-keys"
import { ROUTES } from "@/lib/routes"
import { NotificationToast } from "./components/NotificationToast"
import type { NotificationDto, SignalRNotificationPayload } from "./notificationTypes"

export function useSignalR() {
  const queryClient = useQueryClient()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const navigate = useNavigate()

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
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.all,
      })

      toast.custom((id) =>
        createElement(NotificationToast, {
          type: payload.type,
          message: payload.message,
          dealId: payload.dealId ?? null,
          onView: () => {
            toast.dismiss(id)
            navigate(ROUTES.NOTIFICATIONS)
          },
          onDismiss: () => toast.dismiss(id),
        }),
        { duration: 5000 },
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
  }, [isAuthenticated, queryClient, navigate])
}
