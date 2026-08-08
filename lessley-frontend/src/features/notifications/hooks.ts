import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
import { queryKeys } from "@/lib/query-keys"
import { fetchNotifications, markNotificationRead } from "./api"
import type { NotificationDto } from "./notificationTypes"

export function useNotificationsQuery() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return useQuery({
    queryKey: queryKeys.notifications.list(),
    queryFn: fetchNotifications,
    enabled: isAuthenticated,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  })
}

export function useUnreadCount() {
  const { data: notifications = [] } = useNotificationsQuery()
  return notifications.filter((n) => !n.isRead).length
}

export function useMarkRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: markNotificationRead,
    onSuccess: (_data, notificationId) => {
      queryClient.setQueryData<NotificationDto[]>(
        queryKeys.notifications.list(),
        (old) =>
          old?.map((n) =>
            n.id === notificationId
              ? { ...n, isRead: true, readAt: new Date().toISOString() }
              : n,
          ) ?? [],
      )
    },
  })
}

