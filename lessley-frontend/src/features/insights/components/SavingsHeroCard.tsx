import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"

interface SavingsHeroCardProps {
  totalSaved: number
  periodLabel: string
  clubsCount: number
}

export function SavingsHeroCard({ totalSaved, periodLabel, clubsCount }: SavingsHeroCardProps) {
  const { t } = useTranslation()
  return (
    <div className="surface-navy space-y-4 rounded-3xl p-6 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-navy-muted">{t("insights.savingsHero.label")}</p>
      <p className="text-4xl font-bold">{formatAmount(totalSaved)}</p>
      <p className="text-sm text-navy-muted">
        {periodLabel} · {clubsCount} {clubsCount === 1 ? t("insights.savingsHero.club") : t("insights.savingsHero.clubs")}
      </p>
    </div>
  )
}
