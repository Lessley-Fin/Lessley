import { Bar, BarChart, LabelList, ResponsiveContainer, XAxis } from "recharts"
import { useTranslation } from "react-i18next"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { formatAmount, formatShortDate } from "@/lib/formatters"
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

  const today = new Date()
  const cutoff = new Date(today)
  cutoff.setDate(cutoff.getDate() - days)
  const previousEnd = new Date(cutoff)
  previousEnd.setDate(previousEnd.getDate() - 1)
  const previousStart = new Date(today)
  previousStart.setDate(previousStart.getDate() - days * 2)

  const currentPeriodLabel = `${formatShortDate(cutoff)} – ${formatShortDate(today)}`
  const previousPeriodLabel = `${formatShortDate(previousStart)} – ${formatShortDate(previousEnd)}`

  const data = [
    {
      label: t(""),
      current: comparison.current_period_total,
      previous: comparison.previous_period_total,
    },
  ]

  const currentSpentMore = data[0].current > data[0].previous
  const currentColor = currentSpentMore ? "hsl(var(--destructive))" : "hsl(var(--success))"
  const previousColor = currentSpentMore ? "hsl(var(--success))" : "hsl(var(--destructive))"
  const currentLabelColor = currentSpentMore ? "hsl(var(--destructive-foreground))" : "hsl(var(--success-foreground))"
  const previousLabelColor = currentSpentMore ? "hsl(var(--success-foreground))" : "hsl(var(--destructive-foreground))"

  return (
    <CarouselSlideCard title={t("insights.spendingOverviewSlide.title")} subtitle={t("insights.spendingOverviewSlide.subtitle")}>
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={data} barGap={4}>
          <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={11} />
          <Bar dataKey="previous" fill={previousColor} radius={6}>
            <LabelList
              dataKey="previous"
              position="center"
              fontSize={11}
              fill={previousLabelColor}
              formatter={(value) => formatAmount(Number(value))}
            />
          </Bar>
          <Bar dataKey="current" fill={currentColor} radius={6}>
            <LabelList
              dataKey="current"
              position="center"
              fontSize={11}
              fill={currentLabelColor}
              formatter={(value) => formatAmount(Number(value))}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 text-xs text-muted-foreground">
        <LegendDot color={previousColor} text={previousPeriodLabel} />
        <LegendDot color={currentColor} text={currentPeriodLabel} />
      </div>
    </CarouselSlideCard>
  )
}
