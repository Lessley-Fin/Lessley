import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"
import { cn } from "@/lib/utils"
import type { OptimizerDealSummary, OptimizerResult } from "@/lib/types"
import { StackSteps } from "./StackSteps"

interface RankedOptionsProps {
  results: OptimizerResult[]
  deals: Record<string, OptimizerDealSummary>
}

/** The runner-up stacks — expand one to see the same step breakdown as the winner. */
export function RankedOptions({ results, deals }: RankedOptionsProps) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState<number | null>(null)

  if (results.length === 0) return null

  return (
    <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <div>
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {t("optimizer.rankedOptions.title")}
        </p>
        <p className="text-xs text-muted-foreground">
          {t("optimizer.rankedOptions.subtitle", { count: results.length })}
        </p>
      </div>

      {results.map((result) => {
        const isOpen = expanded === result.rank

        return (
          <div key={result.rank} className="rounded-2xl border border-border">
            <button
              type="button"
              onClick={() => setExpanded(isOpen ? null : result.rank)}
              aria-expanded={isOpen}
              className="flex w-full items-center gap-3 px-3 py-3 text-start"
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-bold">
                {result.rank}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold">{formatAmount(result.final_price)}</span>
                <span className="block text-xs text-muted-foreground">
                  {t("optimizer.rankedOptions.saves", {
                    amount: formatAmount(result.total_savings),
                    count: result.per_step.length,
                  })}
                </span>
              </span>
              <ChevronDown
                className={cn("size-4 shrink-0 text-muted-foreground transition-transform", isOpen && "rotate-180")}
                aria-hidden
              />
            </button>

            {isOpen ? (
              <div className="border-t border-border px-3 py-3">
                <StackSteps steps={result.per_step} deals={deals} />
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
