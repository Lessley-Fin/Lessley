import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Bell } from "lucide-react"

import { EmptyState } from "@/components/shared/EmptyState"
import { LoadingCard } from "@/components/shared/LoadingCard"
import { PageHeader } from "@/components/shared/PageHeader"
import { fintech } from "@/lib/fintech-styles"
import { NotificationRow } from "./components/NotificationRow"
import { useNotificationsQuery, useMarkAllRead } from "./hooks"

export function NotificationsPage() {
  const navigate = useNavigate()
  const { data: notifications = [], isLoading } = useNotificationsQuery()
  const markAllRead = useMarkAllRead()

  useEffect(() => {
    return () => {
      markAllRead.mutate()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const unread = notifications.filter((n) => !n.isRead)
  const read = notifications.filter((n) => n.isRead)

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        title="Notifications"
        subtitle={
          isLoading
            ? "Loading..."
            : unread.length
              ? `${unread.length} unread`
              : "You're all caught up"
        }
        onBack={() => navigate(-1)}
      />

      <div className="flex-1 space-y-6 px-4 py-4">
        {isLoading && notifications.length === 0 ? (
          <LoadingCard message="Loading notifications..." />
        ) : notifications.length === 0 ? (
          <EmptyState icon={Bell} title="No notifications yet." />
        ) : null}

        {unread.length > 0 ? (
          <section className="space-y-2">
            <h3 className={fintech.sectionEyebrow}>Unread</h3>
            <div className="space-y-2">
              {unread.map((item) => (
                <NotificationRow key={item.id} item={item} />
              ))}
            </div>
          </section>
        ) : null}

        {read.length > 0 ? (
          <section className="space-y-2">
            <h3 className={fintech.sectionEyebrow}>Earlier</h3>
            <div className="space-y-2">
              {read.map((item) => (
                <NotificationRow key={item.id} item={item} />
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  )
}
