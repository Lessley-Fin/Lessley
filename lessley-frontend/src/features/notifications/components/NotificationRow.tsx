import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"

import { formatRelativeTime } from "@/lib/formatters"
import { cn } from "@/lib/utils"
import { notificationBadge, notificationHasDetail, notificationTitleKey } from "../helpers"
import type { NotificationDto } from "../notificationTypes"
import { NotificationDetail } from "./NotificationDetail"

interface NotificationRowProps {
  item: NotificationDto
  onRead?: (id: string) => void
}

export function NotificationRow({ item, onRead }: NotificationRowProps) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const hasDetail = notificationHasDetail(item)

  function handleClick() {
    if (!item.isRead && onRead) onRead(item.id)
    if (hasDetail) setExpanded((prev) => !prev)
  }

  return (
    <li
      className={cn(
        "rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]",
        !item.isRead && "ring-2 ring-primary/40",
      )}
    >
      <button type="button" onClick={handleClick} className="w-full text-start">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-secondary px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-secondary-foreground">
            {t(`notifications.badge.${notificationBadge(item)}`)}
          </span>
          {!item.isRead ? <span className="size-2 rounded-full bg-primary" aria-hidden /> : null}
          <span className="ms-auto text-xs text-muted-foreground">{formatRelativeTime(item.sentAt)}</span>
          {hasDetail ? (
            <ChevronDown className={cn("size-4 transition-transform", expanded && "rotate-180")} aria-hidden />
          ) : null}
        </div>
        <p className="mt-2 text-[15px] font-semibold">{t(`notifications.title.${notificationTitleKey(item)}`)}</p>
        <p className="text-sm text-muted-foreground">{item.message}</p>
      </button>
      {expanded && hasDetail ? <NotificationDetail item={item} /> : null}
    </li>
  )
}
