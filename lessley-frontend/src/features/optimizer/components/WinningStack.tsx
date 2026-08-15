import { Trophy } from "lucide-react"
import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"
import type { OptimizerDealSummary, OptimizerResult, OptimizerStore } from "@/lib/types"
import { StackSteps } from "./StackSteps"

interface WinningStackProps {
  result: OptimizerResult
  deals: Record<string, OptimizerDealSummary>
  storeName: string
  store?: OptimizerStore | null
}

export function WinningStack({ result, deals, storeName, store }: WinningStackProps) {
  const { t } = useTranslation()
  const savedRate = result.starting_price > 0 ? result.total_savings / result.starting_price : 0

  return (
    <div className="overflow-hidden rounded-3xl bg-card shadow-[var(--shadow-card)]">
      <div className="surface-teal flex items-center gap-3 p-5">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-card/25">
          <Trophy className="size-4" aria-hidden />
        </div>
        <div>
          <p className="text-sm font-bold">{t("optimizer.winningStack.title")}</p>
          <p className="text-xs opacity-80">
            {t("optimizer.winningStack.subtitle", { count: result.per_step.length, store: storeName })}
          </p>
        </div>
      </div>

      <div className="space-y-4 p-5">
        {/* The number the whole page exists to produce, with the saving it represents. */}
        <div className="text-center">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {t("optimizer.winningStack.youPay")}
          </p>
          <p className="mt-1 text-4xl font-bold text-primary">{formatAmount(result.final_price)}</p>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-2 text-sm">
            <span className="text-muted-foreground line-through">{formatAmount(result.starting_price)}</span>
            <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-bold text-primary">
              {t("optimizer.winningStack.savePill", {
                amount: formatAmount(result.total_savings),
                percent: Math.round(savedRate * 100),
              })}
            </span>
          </div>
        </div>

        <div>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {t("optimizer.winningStack.howItStacks")}
          </p>

          {/* Anchor the chain at both ends so the steps read as a path from
              cart total down to the final price. */}
          <div className="mb-1 flex items-center justify-between rounded-2xl border border-dashed border-border px-3 py-2 text-sm">
            <span className="text-muted-foreground">{t("optimizer.winningStack.cartTotal")}</span>
            <span className="font-semibold">{formatAmount(result.starting_price)}</span>
          </div>

          <StackSteps
            steps={result.per_step}
            deals={deals}
            cartTotal={result.starting_price}
            store={store}
          />

          <div className="mt-1 flex items-center justify-between rounded-2xl bg-secondary px-3 py-2 text-sm">
            <span className="font-semibold">{t("optimizer.winningStack.youPay")}</span>
            <span className="text-base font-bold text-primary">{formatAmount(result.final_price)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
