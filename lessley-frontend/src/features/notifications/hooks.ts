import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
import { NOTIFICATION_POLL_INTERVAL_MS } from "@/lib/constants"
import { queryKeys } from "@/lib/query-keys"
import { fetchNotifications, markAllNotificationsRead } from "./api"
import type { NotificationDto } from "./notificationTypes"

export function useNotificationsQuery() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return useQuery({
    queryKey: queryKeys.notifications.list(),
    queryFn: fetchNotifications,
    enabled: isAuthenticated,
    refetchInterval: NOTIFICATION_POLL_INTERVAL_MS,
  })
}

export function useUnreadCount() {
  const { data: notifications = [] } = useNotificationsQuery()
  return notifications.filter((n) => !n.isRead).length
}

export function useMarkAllRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.setQueryData<NotificationDto[]>(
        queryKeys.notifications.list(),
        (old) =>
          old?.map((n) => ({
            ...n,
            isRead: true,
            readAt: new Date().toISOString(),
          })) ?? [],
      )
    },
  })
}

