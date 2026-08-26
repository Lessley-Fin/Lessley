import { Bar, BarChart, LabelList, ResponsiveContainer, XAxis } from "recharts"
import { Minus, TrendingDown, TrendingUp } from "lucide-react"
import { useTranslation } from "react-i18next"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { formatAmount, formatShortDate } from "@/lib/formatters"
import type { SpendingPeriodComparison } from "@/lib/types"
import { cn } from "@/lib/utils"

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

  // The two windows are only unambiguous without a year while they both sit in the
  // current one — a 30-day comparison in January, or any year-long period, reaches
  // back past New Year and needs the year spelled out.
  const spansYears = previousStart.getFullYear() !== today.getFullYear()
  const shortDate = (date: Date) => formatShortDate(date, { withYear: spansYears })

  const currentPeriodLabel = `${shortDate(cutoff)} – ${shortDate(today)}`
  const previousPeriodLabel = `${shortDate(previousStart)} – ${shortDate(previousEnd)}`

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

  // The takeaway in words, so the bars don't have to be read to get the point.
  // `difference` is current − previous, so positive means this period cost more.
  // Rounding to whole shekels first stops a few agorot of float drift from being
  // announced as a real change, and the percentage is only meaningful when there
  // was something to grow from — with no previous spending we state the amount alone.
  const difference = comparison.difference
  const isFlat = Math.round(Math.abs(difference)) === 0
  const percentChange =
    comparison.previous_period_total > 0
      ? Math.round((Math.abs(difference) / comparison.previous_period_total) * 100)
      : null
  const direction = difference > 0 ? "more" : "less"

  // The sentence names the same four dates the legend shows, so "this period" and
  // "previous" are readable without mapping them back to the colours first.
  const periodDates = {
    currentStart: shortDate(cutoff),
    currentEnd: shortDate(today),
    previousStart: shortDate(previousStart),
    previousEnd: shortDate(previousEnd),
  }

  const summaryText = isFlat
    ? t("insights.spendingOverviewSlide.summary.same", periodDates)
    : percentChange === null
      ? t(`insights.spendingOverviewSlide.summary.${direction}AmountOnly`, {
          amount: formatAmount(Math.abs(difference)),
          ...periodDates,
        })
      : t(`insights.spendingOverviewSlide.summary.${direction}`, {
          amount: formatAmount(Math.abs(difference)),
          percent: percentChange,
          ...periodDates,
        })

  const SummaryIcon = isFlat ? Minus : difference > 0 ? TrendingUp : TrendingDown
  const summaryTone = isFlat ? "text-muted-foreground" : difference > 0 ? "text-destructive" : "text-success"

  return (
    <CarouselSlideCard title={t("insights.spendingOverviewSlide.title")} subtitle={t("insights.spendingOverviewSlide.subtitle")}>
      {/* The card is a fixed 330px with no scroll, and the summary sentence wraps
          to a different number of lines per language and screen width — so the
          chart takes whatever is left rather than a fixed height that could push
          the text out of the card. The floor keeps the bars readable, and stops
          ResponsiveContainer from measuring a zero-height parent on first paint. */}
      <div className="flex h-full flex-col gap-2">
        <div className="min-h-[96px] flex-1">
          <ResponsiveContainer width="100%" height="100%">
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
        </div>
        <div className="flex shrink-0 gap-4 text-xs text-muted-foreground">
          <LegendDot color={previousColor} text={previousPeriodLabel} />
          <LegendDot color={currentColor} text={currentPeriodLabel} />
        </div>
        <div className="flex shrink-0 items-start gap-2 rounded-2xl bg-secondary px-3 py-2">
          <SummaryIcon className={cn("mt-px size-4 shrink-0", summaryTone)} aria-hidden />
          <p className="text-xs leading-snug text-secondary-foreground">{summaryText}</p>
        </div>
        {/* Both bars are the bank figure, so they read against the headline total rather than
            against the per-category breakdowns, which count a coupon at its full worth. */}
        <p className="shrink-0 text-[11px] leading-relaxed text-muted-foreground">
          {t("insights.explain.spendTotal")}
        </p>
      </div>
    </CarouselSlideCard>
  )
}
