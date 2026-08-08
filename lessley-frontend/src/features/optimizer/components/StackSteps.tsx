import { ArrowRight, ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"
import type { OptimizerDealSummary, OptimizerStep } from "@/lib/types"

interface StackStepsProps {
  steps: OptimizerStep[]
  deals: Record<string, OptimizerDealSummary>
}

function formatPercent(rate: number) {
  const percent = rate * 100
  // One decimal only where it carries information: 4.5% stays, 4.0% reads as 4%.
  return `${percent.toFixed(percent < 10 ? 1 : 0).replace(/\.0$/, "")}%`
}

function dealTypeLabel(dealType?: string | null) {
  if (!dealType) return null
  return dealType.replace(/_/g, " ")
}

/**
 * The ordered chain of deals in one stack. Each row is one deal: what it is,
 * the discount it carries, and how it moved the running bill — so the path from
 * cart total to final price can be followed line by line.
 */
export function StackSteps({ steps, deals }: StackStepsProps) {
  const { t } = useTranslation()

  return (
    <ol className="space-y-1">
      {steps.map((step, index) => {
        const deal = deals[step.deal_id]
        const label = dealTypeLabel(deal?.deal_type)
        const isLast = index === steps.length - 1

        return (
          <li key={`${step.deal_id}-${index}`}>
            <div className="rounded-2xl bg-secondary p-3">
              <div className="flex items-start gap-3">
                <span className="surface-teal flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold">
                  {index + 1}
                </span>

                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{deal?.title ?? step.deal_id}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    {label ? <span className="rounded-md bg-card px-1.5 py-0.5 capitalize">{label}</span> : null}
                    {deal?.source_id ? <span>{deal.source_id}</span> : null}
                  </div>
                </div>

                {/* The discount this deal contributes, boxed so it reads at a glance. */}
                <div className="shrink-0 text-end">
                  <span className="block rounded-xl bg-primary/10 px-2.5 py-1 text-sm font-bold text-primary">
                    {t("optimizer.stackSteps.percentOff", { percent: formatPercent(step.discount_rate) })}
                  </span>
                  <span className="mt-1 block text-xs font-semibold text-primary">
                    −{formatAmount(step.savings)}
                  </span>
                </div>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border/60 pt-2 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  {formatAmount(step.bill_before)}
                  <ArrowRight className="size-3 rtl:rotate-180" aria-hidden />
                  <span className="font-semibold text-foreground">{formatAmount(step.bill_after)}</span>
                </span>
                {/* Tender deals only discount the slice of the bill routed through
                    that instrument — price-level deals report null and discount whatever's left. */}
                {step.ils_covered !== null ? (
                  <span>{t("optimizer.stackSteps.coversOfBill", { amount: formatAmount(step.ils_covered) })}</span>
                ) : null}
              </div>

              {/* A tiered loadable card discounts at a rate that steps down as the
                  load grows, so the rate above is a blend. Break it out per rung,
                  otherwise "21.7% off" matches none of the card's actual rates. */}
              {step.segments ? (
                <ul className="mt-2 space-y-1 border-s-2 border-border ps-3 text-xs text-muted-foreground">
                  {step.segments.map((segment) => (
                    <li key={segment.tier_index} className="flex items-baseline gap-1.5">
                      <span className="font-medium text-foreground">{formatAmount(segment.ils_covered)}</span>
                      <span>{t("optimizer.stackSteps.atRate", { rate: formatPercent(segment.rate) })}</span>
                      <span className="text-primary">−{formatAmount(segment.savings)}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>

            {/* Connector: makes the rows read as one chain rather than a flat list. */}
            {!isLast ? (
              <div className="flex justify-center py-0.5" aria-hidden>
                <ChevronDown className="size-3.5 text-muted-foreground" />
              </div>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}
