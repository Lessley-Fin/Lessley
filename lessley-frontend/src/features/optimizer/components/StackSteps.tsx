import { ArrowDown } from "lucide-react"

import { formatAmount } from "@/lib/formatters"
import type { OptimizerDealSummary, OptimizerStep } from "@/lib/types"

interface StackStepsProps {
  steps: OptimizerStep[]
  deals: Record<string, OptimizerDealSummary>
}

function formatPercent(rate: number) {
  return `${(rate * 100).toFixed(rate * 100 < 10 ? 1 : 0)}%`
}

function dealTypeLabel(dealType?: string | null) {
  if (!dealType) return null
  return dealType.replace(/_/g, " ")
}

/** The ordered chain of deals in one stack, with what each step actually saved. */
export function StackSteps({ steps, deals }: StackStepsProps) {
  return (
    <ol className="space-y-2">
      {steps.map((step, index) => {
        const deal = deals[step.deal_id]
        const label = dealTypeLabel(deal?.deal_type)

        return (
          <li key={`${step.deal_id}-${index}`} className="fintech-card-inset">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-800">
                  {deal?.title ?? step.deal_id}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  {label ? (
                    <span className="rounded-md bg-slate-100 px-1.5 py-0.5 capitalize text-slate-600">{label}</span>
                  ) : null}
                  {deal?.source_id ? <span>{deal.source_id}</span> : null}
                </div>
              </div>
              <p className="shrink-0 text-sm font-semibold text-emerald-600">
                −{formatAmount(step.savings)}
              </p>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1">
                {formatAmount(step.bill_before)}
                <ArrowDown className="size-3 rotate-[-90deg]" aria-hidden />
                <span className="font-medium text-slate-700">{formatAmount(step.bill_after)}</span>
              </span>
              <span>{formatPercent(step.discount_rate)} off</span>
              {/* Tender deals only discount the slice of the bill routed through
                  that instrument — price-level deals report null and discount whatever's left. */}
              {step.ils_covered !== null ? (
                <span>covers {formatAmount(step.ils_covered)} of the bill</span>
              ) : null}
            </div>

            {/* A tiered loadable card discounts at a rate that steps down as the
                load grows, so the rate above is a blend. Break it out per rung,
                otherwise "21.7% off" matches none of the card's actual rates. */}
            {step.segments ? (
              <ul className="mt-2 space-y-1 border-l-2 border-slate-200 pl-3 text-xs text-slate-500">
                {step.segments.map((segment) => (
                  <li key={segment.tier_index} className="flex items-baseline gap-1.5">
                    <span className="font-medium text-slate-700">
                      {formatAmount(segment.ils_covered)}
                    </span>
                    <span>at {formatPercent(segment.rate)}</span>
                    <span className="text-emerald-600">−{formatAmount(segment.savings)}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}
