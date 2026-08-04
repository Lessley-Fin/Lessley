import { useState } from "react"
import { ChevronDown, Layers } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { Card, CardContent } from "@/components/ui/card"
import { formatAmount } from "@/lib/formatters"
import { fintech } from "@/lib/fintech-styles"
import { cn } from "@/lib/utils"
import type { OptimizerDealSummary, OptimizerResult } from "@/lib/types"
import { StackSteps } from "./StackSteps"

interface RankedOptionsProps {
  results: OptimizerResult[]
  deals: Record<string, OptimizerDealSummary>
}

/** The runner-up stacks — expand one to see the same step breakdown as the winner. */
export function RankedOptions({ results, deals }: RankedOptionsProps) {
  const [expanded, setExpanded] = useState<number | null>(null)

  if (results.length === 0) return null

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={Layers}
        iconColor="violet"
        title="Other options"
        subtitle={`${results.length} more ranked combination${results.length !== 1 ? "s" : ""}`}
      />
      <CardContent className="space-y-2 px-5 pb-5 pt-2">
        {results.map((result) => {
          const isOpen = expanded === result.rank

          return (
            <div key={result.rank} className="rounded-xl border border-slate-200">
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? null : result.rank)}
                aria-expanded={isOpen}
                className="flex w-full items-center gap-3 px-3 py-3 text-left"
              >
                <span className={fintech.rankBadge}>#{result.rank}</span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-slate-800">
                    {formatAmount(result.final_price)}
                  </span>
                  <span className="block text-xs text-slate-500">
                    saves {formatAmount(result.total_savings)} · {result.per_step.length} deal
                    {result.per_step.length !== 1 ? "s" : ""}
                  </span>
                </span>
                <ChevronDown
                  className={cn("size-4 shrink-0 text-slate-400 transition-transform", isOpen && "rotate-180")}
                  aria-hidden
                />
              </button>

              {isOpen ? (
                <div className="border-t border-slate-100 px-3 py-3">
                  <StackSteps steps={result.per_step} deals={deals} />
                </div>
              ) : null}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
