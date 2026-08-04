import { Trophy } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { formatAmount } from "@/lib/formatters"
import { fintech } from "@/lib/fintech-styles"
import type { OptimizerDealSummary, OptimizerResult } from "@/lib/types"
import { StackSteps } from "./StackSteps"

interface WinningStackProps {
  result: OptimizerResult
  deals: Record<string, OptimizerDealSummary>
  storeName: string
}

export function WinningStack({ result, deals, storeName }: WinningStackProps) {
  const savedRate = result.starting_price > 0 ? result.total_savings / result.starting_price : 0

  return (
    <Card className="fintech-card overflow-hidden border-0">
      <div className="border-b border-slate-100/80 bg-gradient-to-r from-emerald-50 to-blue-50 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className={fintech.iconWrapEmerald}>
            <Trophy className="size-4" />
          </div>
          <div>
            <p className={fintech.sectionTitle}>Best stack</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {storeName} · {result.per_step.length} deal{result.per_step.length !== 1 ? "s" : ""} applied
            </p>
          </div>
        </div>
      </div>

      <CardContent className="space-y-4 px-5 pb-5 pt-4">
        <div className="grid grid-cols-3 gap-2">
          <div className={fintech.metric}>
            <p className={fintech.metricValue}>{formatAmount(result.starting_price)}</p>
            <p className={fintech.metricLabel}>Cart total</p>
          </div>
          <div className={fintech.metricEmerald}>
            <p className={fintech.metricValue}>{formatAmount(result.final_price)}</p>
            <p className={fintech.metricLabel}>You pay</p>
          </div>
          <div className={fintech.metricViolet}>
            <p className={fintech.metricValue}>{formatAmount(result.total_savings)}</p>
            <p className={fintech.metricLabel}>Saved ({Math.round(savedRate * 100)}%)</p>
          </div>
        </div>

        <div>
          <p className={fintech.sectionEyebrow}>How it stacks</p>
          <div className="mt-2">
            <StackSteps steps={result.per_step} deals={deals} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
