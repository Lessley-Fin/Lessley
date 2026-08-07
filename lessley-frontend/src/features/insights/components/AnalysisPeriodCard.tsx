import { TIME_RANGE_OPTIONS } from "@/lib/constants"
import { cn } from "@/lib/utils"

interface AnalysisPeriodCardProps {
  value: number
  onChange: (days: number) => void
}

export function AnalysisPeriodCard({ value, onChange }: AnalysisPeriodCardProps) {
  return (
    <div className="no-scrollbar flex items-center gap-1 overflow-x-auto rounded-full border border-border bg-card p-1 text-sm">
      {TIME_RANGE_OPTIONS.map((opt) => (
        <button
          key={opt.days}
          type="button"
          onClick={() => onChange(opt.days)}
          className={cn(
            "flex-1 rounded-full whitespace-nowrap px-3 py-2 font-medium transition-colors",
            value === opt.days ? "surface-navy shadow-[var(--shadow-card)]" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
