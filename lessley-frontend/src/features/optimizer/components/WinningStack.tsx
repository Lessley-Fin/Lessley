import { Trophy } from "lucide-react"
import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"
import type { OptimizerDealSummary, OptimizerResult } from "@/lib/types"
import { StackSteps } from "./StackSteps"

interface WinningStackProps {
  result: OptimizerResult
  deals: Record<string, OptimizerDealSummary>
  storeName: string
}

export function WinningStack({ result, deals, storeName }: WinningStackProps) {
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
        <div className="grid grid-cols-3 gap-2 text-center">
          <Metric label={t("optimizer.winningStack.cartTotal")} value={formatAmount(result.starting_price)} />
          <Metric label={t("optimizer.winningStack.youPay")} value={formatAmount(result.final_price)} accent />
          <Metric
            label={t("optimizer.winningStack.saved", { percent: Math.round(savedRate * 100) })}
            value={formatAmount(result.total_savings)}
            accent
          />
        </div>

        <div>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {t("optimizer.winningStack.howItStacks")}
          </p>
          <StackSteps steps={result.per_step} deals={deals} />
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-2xl bg-secondary p-3">
      <p className={accent ? "text-base font-bold text-primary" : "text-base font-bold"}>{value}</p>
      <p className="mt-0.5 text-[11px] text-muted-foreground">{label}</p>
    </div>
  )
}
