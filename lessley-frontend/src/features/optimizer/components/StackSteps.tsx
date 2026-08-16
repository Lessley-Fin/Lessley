import { useState } from "react"
import { ChevronDown, ExternalLink, Info } from "lucide-react"
import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"
import type { OptimizerDealSummary, OptimizerStep, OptimizerStore } from "@/lib/types"
import { DealInfoDialog } from "./DealInfoDialog"

interface StackStepsProps {
  steps: OptimizerStep[]
  deals: Record<string, OptimizerDealSummary>
  /** The original cart total — every step's headline rate is a share of this. */
  cartTotal: number
  store?: OptimizerStore | null
}

function formatPercent(rate: number) {
  const percent = rate * 100
  // One decimal only where it carries information: 4.5% stays, 4.0% reads as 4%.
  return `${percent.toFixed(percent < 10 ? 1 : 0).replace(/\.0$/, "")}%`
}

function useDealTypeLabel() {
  const { t } = useTranslation()
  return (dealType?: string | null) =>
    dealType ? t(`shared.dealTypes.${dealType}`, { defaultValue: dealType.replace(/_/g, " ") }) : null
}

/**
 * The ordered chain of deals in one stack. Each row states the sum the discount
 * is taken off, what's actually paid on that sum, and where the running bill
 * lands — so the path from cart total to final price can be read line by line.
 */
export function StackSteps({ steps, deals, cartTotal, store }: StackStepsProps) {
  const { t } = useTranslation()
  const dealTypeLabel = useDealTypeLabel()
  const [openStep, setOpenStep] = useState<number | null>(null)

  const activeStep = openStep === null ? null : (steps[openStep] ?? null)
  const activeDeal = activeStep ? (deals[activeStep.deal_id] ?? null) : null

  return (
    <>
      <ol className="space-y-1">
        {steps.map((step, index) => {
          const deal = deals[step.deal_id]
          const label = dealTypeLabel(deal?.deal_type)
          const isLast = index === steps.length - 1
          // A tender deal only discounts the slice of the bill routed through that
          // instrument; a price-level deal reports null and works off the whole bill.
          const isPartial = step.ils_covered !== null
          const discountBase = step.ils_covered ?? step.bill_before

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

                  {/* The discount this deal contributes, boxed so it reads at a glance.
                      Deliberately a share of the ORIGINAL cart total, not of the slice
                      this deal covered (`discount_rate`): a card capped at 2,200 on a
                      5,000 cart saves 120, which is 5.5% of what it covered but 2.4% of
                      what you came to spend. The badges are read side by side, so they
                      have to share one denominator or they can't be compared — and the
                      per-deal figures now sum to the stack's headline saving. */}
                  <div className="shrink-0 text-end">
                    <span className="block rounded-xl bg-primary/10 px-2.5 py-1 text-sm font-bold text-primary">
                      {t("optimizer.stackSteps.percentOff", {
                        percent: formatPercent(cartTotal > 0 ? step.savings / cartTotal : 0),
                      })}
                    </span>
                    <span className="mt-1 block text-xs font-semibold text-primary">
                      −{formatAmount(step.savings)}
                    </span>
                  </div>
                </div>

                {/* The three numbers the discount is actually made of. */}
                <dl className="mt-2 space-y-1 border-t border-border/60 pt-2 text-xs">
                  <MoneyRow
                    label={t("optimizer.stackSteps.discountAppliesTo")}
                    value={formatAmount(discountBase)}
                  />
                  {isPartial ? (
                    <MoneyRow
                      label={t("optimizer.stackSteps.youPayOnIt")}
                      value={formatAmount(step.amount_paid_on_covered)}
                    />
                  ) : null}
                  <MoneyRow
                    label={t("optimizer.stackSteps.billLeftToPay")}
                    value={formatAmount(step.bill_after)}
                    was={formatAmount(step.bill_before)}
                  />
                </dl>

                {/* A tiered loadable card discounts at a rate that steps down as the
                    load grows. Neither rung matches the headline badge — that's a share
                    of the whole cart — so the real rates are spelled out here. */}
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

                <div className="mt-2 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setOpenStep(index)}
                    className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2.5 py-1 text-xs font-medium"
                  >
                    <Info className="size-3" aria-hidden />
                    {t("optimizer.stackSteps.moreInfo")}
                  </button>
                  {deal?.url ? (
                    <a
                      href={deal.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2.5 py-1 text-xs font-medium text-primary"
                    >
                      <ExternalLink className="size-3" aria-hidden />
                      {t("optimizer.stackSteps.openDeal")}
                    </a>
                  ) : null}
                </div>
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

      <DealInfoDialog
        deal={activeDeal}
        step={activeStep}
        store={store}
        open={openStep !== null}
        onOpenChange={(open) => !open && setOpenStep(null)}
      />
    </>
  )
}

function MoneyRow({ label, value, was }: { label: string; value: string; was?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="flex items-baseline gap-1.5">
        {was ? <span className="text-muted-foreground line-through">{was}</span> : null}
        <span className="font-semibold text-foreground">{value}</span>
      </dd>
    </div>
  )
}
