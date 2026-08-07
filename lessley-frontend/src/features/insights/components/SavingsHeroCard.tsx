import { formatAmount } from "@/lib/formatters"

interface SavingsHeroCardProps {
  totalSaved: number
  totalSpend: number
  periodLabel: string
  clubsCount: number
}

export function SavingsHeroCard({ totalSaved, totalSpend, periodLabel, clubsCount }: SavingsHeroCardProps) {
  const ratePct = totalSpend > 0 ? Math.min(100, (totalSaved / totalSpend) * 100) : 0

  return (
    <div className="surface-navy space-y-4 rounded-3xl p-6 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-navy-muted">Saved with Lessley</p>
      <p className="text-4xl font-bold">{formatAmount(totalSaved)}</p>
      <p className="text-sm text-navy-muted">
        {periodLabel} · {clubsCount} {clubsCount === 1 ? "club" : "clubs"}
      </p>
      <div className="flex items-center gap-4 pt-2">
        <div
          className="flex size-24 shrink-0 items-center justify-center rounded-full"
          style={{
            background: `conic-gradient(hsl(var(--primary)) ${ratePct * 3.6}deg, hsl(var(--navy-foreground) / 0.12) 0deg)`,
          }}
        >
          <div className="flex size-[74px] items-center justify-center rounded-full bg-navy text-lg font-bold">
            {Math.round(ratePct)}%
          </div>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-navy-muted">Savings rate</p>
          <p className="text-sm">
            <span className="font-bold">{formatAmount(totalSaved)}</span> saved on {formatAmount(totalSpend)} spent
            this period.
          </p>
        </div>
      </div>
    </div>
  )
}
