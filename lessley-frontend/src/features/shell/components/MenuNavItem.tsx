import type { LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"

interface MenuNavItemProps {
  label: string
  icon: LucideIcon
  active?: boolean
  badge?: number
  showUnreadDot?: boolean
  onClick: () => void
}

function UnreadDot({ className }: { className?: string }) {
  return (
    <span
      className={cn("absolute size-2.5 rounded-full bg-rose-500 ring-2 ring-white", className)}
      aria-hidden
    />
  )
}

export function MenuNavItem({ label, icon: Icon, active, badge, showUnreadDot, onClick }: MenuNavItemProps) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className={cn(
        "relative flex w-full shrink-0 items-center gap-3 rounded-xl px-4 py-3 text-left text-[15px] font-medium transition-colors",
        active
          ? "bg-gradient-to-r from-blue-500 to-violet-500 text-white shadow-md"
          : "text-slate-700 hover:bg-violet-50 active:bg-violet-100/80"
      )}
    >
      <span
        className={cn(
          "relative flex size-8 shrink-0 items-center justify-center rounded-lg",
          active ? "bg-white/15 text-white" : "bg-slate-100 text-slate-600"
        )}
      >
        <Icon className="size-[18px] stroke-[2]" aria-hidden />
        {showUnreadDot ? <UnreadDot className="-right-0.5 -top-0.5" /> : null}
      </span>
      <span className="flex-1">{label}</span>
      {badge && badge > 0 ? (
        <span className="rounded-full bg-rose-500 px-2 py-0.5 text-[10px] font-bold text-white tabular-nums">
          {badge > 9 ? "9+" : badge}
        </span>
      ) : null}
    </button>
  )
}

export { UnreadDot }
