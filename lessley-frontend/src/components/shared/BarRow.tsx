import { cn } from "@/lib/utils"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount } from "@/lib/formatters"

interface BarRowProps {
  label: string
  value: number
  maxValue: number
  colorClassName?: string
}

export function BarRow({ label, value, maxValue, colorClassName = "bg-blue-500" }: BarRowProps) {
  const pct = maxValue > 0 ? Math.min(100, Math.max(0, (value / maxValue) * 100)) : 0

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="truncate font-medium text-slate-700">{label}</span>
        <span className={cn(fintech.amount, "shrink-0 text-xs")}>{formatAmount(value)}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className={cn("h-2 rounded-full", colorClassName)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
