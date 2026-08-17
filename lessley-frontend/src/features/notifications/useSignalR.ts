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
      .withUrl("/hubs/notifications", {
        // Auth rides the httpOnly cookie; the gateway reads it for /hubs connections.
        withCredentials: true,
      })
      .withAutomaticReconnect([0, 2000, 5000, 10000, 30000])
      .configureLogging(LogLevel.Warning)
      .build()

    // Toasts are shown one at a time, in arrival order: the next one appears
    // as soon as the current one closes. Advancing the queue is deferred by a
    // tick (not called straight from onDismiss) because sonner re-subscribes
    // its internal toast list on every change, and creating the next toast
    // synchronously during that window can silently drop it.
    const toastQueue: SignalRNotificationPayload[] = []
    let toastActive = false
    let advanceTimeoutId: ReturnType<typeof setTimeout> | undefined

    const showNextToast = () => {
      const payload = toastQueue.shift()
      if (!payload) return
      toastActive = true

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
        {
          duration: Infinity,
          onDismiss: () => {
            toastActive = false
            advanceTimeoutId = setTimeout(showNextToast, 0)
          },
        },
      )
    }

    const handleIncoming = (payload: SignalRNotificationPayload) => {
      const newNotification: NotificationDto = {
        id: crypto.randomUUID(),
        message: payload.message,
        dealId: payload.dealId ?? null,
        sentAt: payload.timestamp,
        type: payload.type,
        calcType: payload.calcType ?? null,
        data: null,
        isRead: false,
        readAt: null,
        categories: payload.categories ?? null,
      }
      queryClient.setQueryData<NotificationDto[]>(
        queryKeys.notifications.list(),
        (old) => [newNotification, ...(old ?? [])],
      )
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.all,
      })

      toastQueue.push(payload)
      if (!toastActive) showNextToast()
    }

    // Categories were recalculated server-side. Not a notification — nothing is stored and
    // nothing is shown; the user did not ask for this and does not need telling. It exists so
    // the screen stops showing figures the database has already moved past.
    const refreshCategories = () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.insights.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.user.profile() })
    }

    connection.on("DealUserNotification", handleIncoming)
    connection.on("DealGroupNotification", handleIncoming)
    connection.on("CalcNotification", handleIncoming)
    connection.on("CategoriesUpdated", refreshCategories)

    connection.onreconnected(() => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.all,
      })
      // Anything that happened while this tab was disconnected arrived nowhere. The two cases
      // that matter both disconnect by design: the bank journey navigates the browser away,
      // and the weekly sweep runs at midnight when nobody is looking.
      refreshCategories()
    })
    connection.onreconnecting(() => {})
    connection.onclose(() => {})

    void connection.start()

    return () => {
      connection.off("DealUserNotification")
      connection.off("DealGroupNotification")
      connection.off("CalcNotification")
      connection.off("CategoriesUpdated")
      clearTimeout(advanceTimeoutId)
      toastQueue.length = 0
      if (connection.state !== HubConnectionState.Disconnected) {
        void connection.stop()
      }
    }
  }, [isAuthenticated, queryClient, navigate])
}
