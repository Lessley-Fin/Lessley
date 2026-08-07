import { Bar, BarChart, ResponsiveContainer, XAxis } from "recharts"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import type { SpendingPeriodComparison } from "@/lib/types"

interface SpendingOverviewSlideProps {
  comparison: SpendingPeriodComparison | null
}

function LegendDot({ color, text }: { color: string; text: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-2.5 rounded-full" style={{ background: color }} />
      {text}
    </span>
  )
}

export function SpendingOverviewSlide({ comparison }: SpendingOverviewSlideProps) {
  if (!comparison) {
    return (
      <CarouselSlideCard title="Spending overview" subtitle="This period vs previous">
        <p className="text-sm text-muted-foreground">Not enough history yet to compare periods.</p>
      </CarouselSlideCard>
    )
  }

  const data = [
    { label: "This period", current: comparison.current_period_total, previous: comparison.previous_period_total },
  ]

  return (
    <CarouselSlideCard title="Spending overview" subtitle="This period vs previous">
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={data} barGap={4}>
          <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={11} />
          <Bar dataKey="previous" fill="hsl(var(--chart-3))" radius={6} />
          <Bar dataKey="current" fill="hsl(var(--chart-1))" radius={6} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 text-xs text-muted-foreground">
        <LegendDot color="hsl(var(--chart-1))" text="Current" />
        <LegendDot color="hsl(var(--chart-3))" text="Previous" />
      </div>
    </CarouselSlideCard>
  )
}
