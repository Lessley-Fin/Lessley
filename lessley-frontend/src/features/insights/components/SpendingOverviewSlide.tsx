import { Bar, BarChart, ResponsiveContainer, XAxis } from "recharts"
import { useTranslation } from "react-i18next"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import type { SpendingPeriodComparison } from "@/lib/types"

interface SpendingOverviewSlideProps {
  comparison: SpendingPeriodComparison | null
  days: number
}

function LegendDot({ color, text }: { color: string; text: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-2.5 rounded-full" style={{ background: color }} />
      {text}
    </span>
  )
}

export function SpendingOverviewSlide({ comparison, days }: SpendingOverviewSlideProps) {
  const { t } = useTranslation()
  if (!comparison) {
    return (
      <CarouselSlideCard title={t("insights.spendingOverviewSlide.title")} subtitle={t("insights.spendingOverviewSlide.subtitle")}>
        <p className="text-sm text-muted-foreground">{t("insights.spendingOverviewSlide.empty")}</p>
      </CarouselSlideCard>
    )
  }

  const isYear = days === 365
  const currentPeriodLabel = isYear
    ? t("insights.spendingOverviewSlide.currentYear")
    : t("insights.spendingOverviewSlide.currentDays", { count: days })
  const previousPeriodLabel = isYear
    ? t("insights.spendingOverviewSlide.previousYear")
    : t("insights.spendingOverviewSlide.previousDays", { count: days })

  const data = [
    {
      label: t("insights.spendingOverviewSlide.thisPeriod"),
      current: comparison.current_period_total,
      previous: comparison.previous_period_total,
    },
  ]

  return (
    <CarouselSlideCard title={t("insights.spendingOverviewSlide.title")} subtitle={t("insights.spendingOverviewSlide.subtitle")}>
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={data} barGap={4}>
          <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={11} />
          <Bar dataKey="previous" fill="hsl(var(--chart-3))" radius={6} />
          <Bar dataKey="current" fill="hsl(var(--chart-1))" radius={6} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 text-xs text-muted-foreground">
        <LegendDot color="hsl(var(--chart-1))" text={currentPeriodLabel} />
        <LegendDot color="hsl(var(--chart-3))" text={previousPeriodLabel} />
      </div>
    </CarouselSlideCard>
  )
}
