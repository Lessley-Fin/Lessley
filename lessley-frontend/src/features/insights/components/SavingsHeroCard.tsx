import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"
import type { SourceBreakdownEntry } from "@/lib/types"

interface SavingsHeroCardProps {
  totalSaved: number
  /** Where the total came from — coupon at the whole price, statement at the gap. */
  breakdown: SourceBreakdownEntry[]
  periodLabel: string
  clubsCount: number
}

export function SavingsHeroCard({ totalSaved, breakdown, periodLabel, clubsCount }: SavingsHeroCardProps) {
  const { t } = useTranslation()
  const counted = breakdown.filter((entry) => entry.count > 0)

  return (
    <div className="surface-navy space-y-4 rounded-3xl p-6 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-navy-muted">
        {t("insights.savingsHero.label")}
      </p>
      <p className="text-4xl font-bold">{formatAmount(totalSaved)}</p>

      {counted.length > 0 && (
        <ul className="space-y-1">
          {counted.map((entry) => (
            <li key={entry.source} className="flex items-baseline justify-between gap-3 text-sm">
              <span className="text-navy-muted">
                {t(`insights.transactionKinds.${entry.source}.label`)}
                <span className="ms-1 text-xs opacity-70">
                  {t("insights.savingsHero.purchaseCount", { count: entry.count })}
                </span>
              </span>
              <span className="font-semibold">{formatAmount(entry.amount)}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Inline rather than behind an info button: what a total leaves out is part of reading
          it, and nobody opens a dialog to find out why a number is smaller than they expected. */}
      <p className="text-xs leading-relaxed text-navy-muted">{t("insights.explain.savedTotal")}</p>

      <p className="text-sm text-navy-muted">
        {periodLabel} · {clubsCount} {clubsCount === 1 ? t("insights.savingsHero.club") : t("insights.savingsHero.clubs")}
      </p>
    </div>
  )
}
