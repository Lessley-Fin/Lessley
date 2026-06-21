import { formatRelativeTime } from "@/lib/formatters"
import { cn } from "@/lib/utils"
import type { NotificationDto } from "../notificationTypes"

function typeAccent(type: string) {
  return type === "group"
    ? "border-violet-200/80 bg-violet-50 text-violet-800"
    : "border-sky-200/80 bg-sky-50 text-sky-800"
}

export function NotificationRow({ item }: { item: NotificationDto }) {
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
            <span className="text-xs text-slate-400 tabular-nums">{formatRelativeTime(item.sentAt)}</span>
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
