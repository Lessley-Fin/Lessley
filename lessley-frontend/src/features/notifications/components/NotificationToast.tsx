import { Bell, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface NotificationToastProps {
  type: string
  message: string
  dealId: string | null
  onView: () => void
  onDismiss: () => void
}

function typeAccent(type: string) {
  return type === "group"
    ? "border-violet-200/80 bg-violet-50 text-violet-800"
    : "border-sky-200/80 bg-sky-50 text-sky-800"
}

export function NotificationToast({ type, message, dealId, onView, onDismiss }: NotificationToastProps) {
  return (
    <div className="w-[min(22rem,calc(100vw-2rem))] animate-[slideDown_0.3s_ease-out] overflow-hidden rounded-2xl border border-violet-200/80 bg-white shadow-[0_4px_24px_hsl(250_95%_58%_/0.12),0_12px_32px_hsl(262_83%_58%_/0.10)]">
      <div className="bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-600 px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-white">
            <Bell className="size-3.5" />
            <span className="text-xs font-semibold tracking-wide">New Notification</span>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            className="rounded-lg p-0.5 text-white/70 transition-colors hover:bg-white/20 hover:text-white"
            aria-label="Dismiss"
          >
            <X className="size-3.5" />
          </button>
        </div>
      </div>

      <button type="button" onClick={onView} className="w-full px-4 py-3 text-left transition-colors hover:bg-slate-50/80">
        <div className="flex items-start gap-3">
          <span className="mt-1 size-2 shrink-0 rounded-full bg-violet-500" aria-hidden />
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "inline-flex rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  typeAccent(type),
                )}
              >
                {type === "group" ? "Group" : "Direct"}
              </span>
              <span className="text-[10px] text-slate-400">Just now</span>
            </div>
            <p className="text-sm font-medium leading-relaxed text-slate-800">{message}</p>
            {dealId ? (
              <p className="truncate text-xs text-slate-400">Deal · {dealId}</p>
            ) : null}
          </div>
        </div>
      </button>
    </div>
  )
}
