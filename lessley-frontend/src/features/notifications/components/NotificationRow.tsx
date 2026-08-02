import { useState } from "react"
import { ChevronDown } from "lucide-react"

import { formatRelativeTime } from "@/lib/formatters"
import { cn } from "@/lib/utils"
import type { NotificationDto } from "../notificationTypes"
import { NotificationDetail } from "./NotificationDetail"

function typeAccent(type: string) {
  return type === "group"
    ? "border-violet-200/80 bg-violet-50 text-violet-800"
    : "border-sky-200/80 bg-sky-50 text-sky-800"
}

interface NotificationRowProps {
  item: NotificationDto
  onRead?: (id: string) => void
}

export function NotificationRow({ item, onRead }: NotificationRowProps) {
  const [expanded, setExpanded] = useState(false)

  const handleClick = () => {
    if (!item.isRead && onRead) {
      onRead(item.id)
    }
    setExpanded((prev) => !prev)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "fintech-card cursor-pointer rounded-2xl p-4 transition-shadow active:scale-[0.99]",
        item.isRead
          ? "border-slate-200/60"
          : "border-violet-200/80 bg-violet-50/50 ring-1 ring-violet-100",
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
              {item.type === "group" ? "Group" : item.type === "calc" ? "Analysis" : "Direct"}
            </span>
            <span className="text-xs text-slate-400 tabular-nums">{formatRelativeTime(item.sentAt)}</span>
          </div>
          <p className={cn("text-sm leading-relaxed", item.isRead ? "text-slate-600" : "font-medium text-slate-800")}>
            {item.message}
          </p>

          {expanded ? <NotificationDetail item={item} /> : null}
        </div>

        <ChevronDown
          className={cn(
            "mt-1.5 size-4 shrink-0 text-slate-400 transition-transform duration-200",
            expanded && "rotate-180",
          )}
        />
      </div>
    </div>
  )
}
