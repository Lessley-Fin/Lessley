import { Bell } from "lucide-react"

import { NotificationRow } from "./components/NotificationRow"
import { useMarkRead, useNotificationsQuery } from "./hooks"

export function NotificationsPage() {
  const { data: notifications = [], isLoading } = useNotificationsQuery()
  const markRead = useMarkRead()
  const unreadCount = notifications.filter((n) => !n.isRead).length

  function handleRead(id: string) {
    markRead.mutate(id)
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
        <p className="text-sm text-muted-foreground">
          {isLoading ? "Loading..." : unreadCount > 0 ? `${unreadCount} unread` : "You're all caught up"}
        </p>
      </div>

      {!isLoading && notifications.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-secondary">
            <Bell className="size-7 text-muted-foreground" aria-hidden />
          </div>
          <p className="text-sm text-muted-foreground">No notifications yet.</p>
        </div>
      ) : (
        <ul className="no-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto pb-2">
          {notifications.map((item) => (
            <NotificationRow key={item.id} item={item} onRead={handleRead} />
          ))}
        </ul>
      )}
    </div>
  )
}
