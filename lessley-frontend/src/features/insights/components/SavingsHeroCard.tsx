import { formatAmount } from "@/lib/formatters"

interface SavingsHeroCardProps {
  totalSaved: number
  periodLabel: string
  clubsCount: number
}

export function SavingsHeroCard({ totalSaved, periodLabel, clubsCount }: SavingsHeroCardProps) {
  return (
    <div className="surface-navy space-y-4 rounded-3xl p-6 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-navy-muted">Saved with Lessley</p>
      <p className="text-4xl font-bold">{formatAmount(totalSaved)}</p>
      <p className="text-sm text-navy-muted">
        {periodLabel} · {clubsCount} {clubsCount === 1 ? "club" : "clubs"}
      </p>
    </div>
  )
}
