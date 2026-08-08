import { useCallback, useEffect, useRef, useState } from "react"
import { Bell, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"

const VISIBLE_MS = 5000
const EXIT_ANIM_MS = 300

interface NotificationToastProps {
  type: string
  message: string
  dealId: string | null
  onView: () => void
  onDismiss: () => void
}

export function NotificationToast({ type, message, dealId, onView, onDismiss }: NotificationToastProps) {
  const { t } = useTranslation()
  const [exiting, setExiting] = useState(false)
  const onDismissRef = useRef(onDismiss)

  useEffect(() => {
    onDismissRef.current = onDismiss
  }, [onDismiss])

  const triggerExit = useCallback((callback: () => void) => {
    setExiting(true)
    setTimeout(callback, EXIT_ANIM_MS)
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      triggerExit(() => onDismissRef.current())
    }, VISIBLE_MS)
    return () => clearTimeout(timer)
  }, [triggerExit])

  return (
    <div
      className={cn(
        "fintech-card w-[min(22rem,calc(100vw-2rem))] border-white/90",
        exiting
          ? "animate-[slideUp_0.3s_ease-in_forwards]"
          : "animate-[slideDown_0.3s_ease-out]",
      )}
    >
      <div className="surface-teal flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2">
          <Bell className="size-3.5" aria-hidden />
          <span className="text-xs font-semibold tracking-wide">{t("notifications.toast.newNotification")}</span>
        </div>
        <button
          type="button"
          onClick={() => triggerExit(onDismiss)}
          className="rounded-lg p-0.5 text-primary-foreground/70 transition-colors hover:bg-white/20 hover:text-primary-foreground"
          aria-label={t("notifications.toast.dismiss")}
        >
          <X className="size-3.5" />
        </button>
      </div>

      <button type="button" onClick={() => triggerExit(onView)} className="w-full px-4 py-3 text-start transition-colors hover:bg-secondary/60">
        <div className="flex items-start gap-3">
          <span className="mt-1 size-2 shrink-0 rounded-full bg-primary" aria-hidden />
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded-full bg-secondary px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-secondary-foreground">
                {type === "group" ? t("notifications.toast.group") : t("notifications.toast.direct")}
              </span>
              <span className="text-[10px] text-muted-foreground">{t("notifications.toast.justNow")}</span>
            </div>
            <p className="text-sm font-medium leading-relaxed text-foreground">{message}</p>
            {dealId ? (
              <p className="truncate text-xs text-muted-foreground">
                {t("notifications.toast.deal")} · {dealId}
              </p>
            ) : null}
          </div>
        </div>
      </button>

      <div className="h-1 w-full bg-secondary">
        <div
          className="h-full rounded-full bg-primary"
          style={{ animation: `toastProgress ${VISIBLE_MS}ms linear forwards` }}
        />
      </div>
    </div>
  )
}
