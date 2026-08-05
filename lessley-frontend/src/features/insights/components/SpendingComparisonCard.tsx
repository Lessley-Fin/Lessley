import { ArrowLeftRight } from "lucide-react"

import { BarRow } from "@/components/shared/BarRow"
import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { Card, CardContent } from "@/components/ui/card"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount } from "@/lib/formatters"
import type { SpendingPeriodComparison } from "@/lib/types"

interface SpendingComparisonCardProps {
  comparison: SpendingPeriodComparison | null
}

export function SpendingComparisonCard({ comparison }: SpendingComparisonCardProps) {
  if (!comparison) return null

  const { current_period_total, previous_period_total, difference } = comparison
  const maxValue = Math.max(current_period_total, previous_period_total, 0)
  const increased = difference > 0

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={ArrowLeftRight}
        iconColor="violet"
        title="Spending vs. previous period"
      />
      <CardContent className="space-y-3 px-5 pb-5 pt-0">
        <BarRow
          label="Current period"
          value={current_period_total}
          maxValue={maxValue}
          colorClassName="bg-violet-500"
        />
        <BarRow
          label="Previous period"
          value={previous_period_total}
          maxValue={maxValue}
          colorClassName="bg-slate-400"
        />
        <div className={increased ? fintech.metricAmber : fintech.metricEmerald}>
          <p className={fintech.metricLabel}>
            {increased ? "Spending increased by" : "Spending decreased by"}
          </p>
          <p className={fintech.metricValue}>{formatAmount(Math.abs(difference))}</p>
        </div>
      </CardContent>
    </Card>
  )
}
