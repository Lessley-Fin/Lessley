import { useEffect } from "react"

import { ArrowLeft, Bell, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import type { NotificationDto } from "@/features/notifications/notificationTypes"
import { fintech } from "@/lib/fintech-styles"
import { cn } from "@/lib/utils"

interface NotificationsPageProps {
  notifications: NotificationDto[]
  isLoading: boolean
  onBack: () => void
  onMarkAllRead: () => void
}

function formatTime(isoDate: string) {
  try {
    const date = new Date(isoDate)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60_000)

    if (diffMin < 1) return "Just now"
    if (diffMin < 60) return `${diffMin}m ago`

    const diffHours = Math.floor(diffMin / 60)
    if (diffHours < 24) return `${diffHours}h ago`

    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "2-digit" })
  } catch {
    return isoDate
  }
}

function typeAccent(type: string) {
  return type === "group"
    ? "border-violet-200/80 bg-violet-50 text-violet-800"
    : "border-sky-200/80 bg-sky-50 text-sky-800"
}

function NotificationRow({ item }: { item: NotificationDto }) {
  return (
    <div
      className={cn(
        "fintech-card rounded-2xl p-4 transition-shadow",
        item.isRead ? "border-slate-200/60" : "border-violet-200/80 bg-violet-50/50 ring-1 ring-violet-100"
      )}
    >
      <div className="flex items-start gap-3">
        {!item.isRead ? (
          <span className="mt-2 size-2 shrink-0 rounded-full bg-violet-500" aria-hidden />
        ) : (
          <span className="mt-2 size-2 shrink-0" aria-hidden />
        )}
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "inline-flex rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                typeAccent(item.type)
              )}
            >
              {item.type === "group" ? "Group" : "Direct"}
            </span>
            <span className="text-xs text-slate-400 tabular-nums">{formatTime(item.sentAt)}</span>
          </div>
          <p className={cn("text-sm leading-relaxed", item.isRead ? "text-slate-600" : "font-medium text-slate-800")}>
            {item.message}
          </p>
          {item.dealId ? (
            <p className="truncate text-xs text-slate-400">Deal · {item.dealId}</p>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export function NotificationsPage({ notifications, isLoading, onBack, onMarkAllRead }: NotificationsPageProps) {
  useEffect(() => {
    return () => {
      onMarkAllRead()
    }
  }, [onMarkAllRead])

  const unread = notifications.filter((n) => !n.isRead)
  const read = notifications.filter((n) => n.isRead)

  return (
    <div className="flex min-h-full flex-col">
      <header className={fintech.subheader}>
        <Button
          type="button"
          variant="ghost"
          className="min-h-10 min-w-10 rounded-xl border border-slate-200/80 bg-white px-0 shadow-sm"
          onClick={onBack}
          aria-label="Back"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-bold tracking-tight text-slate-900">Notifications</h2>
          <p className="text-xs text-slate-500">
            {isLoading
              ? "Loading…"
              : unread.length
                ? `${unread.length} unread`
                : "You're all caught up"}
          </p>
        </div>
      </header>

      <div className="flex-1 space-y-6 px-4 py-4">
        {isLoading && notifications.length === 0 ? (
          <Card className="fintech-card border-0">
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <Loader2 className="size-7 animate-spin text-violet-400" />
              <p className="text-sm text-slate-500">Loading notifications…</p>
            </CardContent>
          </Card>
        ) : notifications.length === 0 ? (
          <Card className="fintech-card border-0">
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <div className="flex size-14 items-center justify-center rounded-2xl bg-slate-100">
                <Bell className="size-7 text-slate-300" />
              </div>
              <p className="text-sm text-slate-500">No notifications yet.</p>
            </CardContent>
          </Card>
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
