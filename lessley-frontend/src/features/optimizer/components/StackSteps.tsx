import { useState } from "react"
import { ChevronDown, ExternalLink, Info } from "lucide-react"
import { useTranslation } from "react-i18next"

import { useClubs } from "@/features/clubs/hooks"
import { getClubLogo } from "@/lib/club-logos"
import { resolveClubName } from "@/lib/clubs"
import { formatAmount } from "@/lib/formatters"
import { cn } from "@/lib/utils"
import type { OptimizerDealSummary, OptimizerStep, OptimizerStore } from "@/lib/types"
import { DealInfoDialog } from "./DealInfoDialog"

interface StackStepsProps {
  steps: OptimizerStep[]
  deals: Record<string, OptimizerDealSummary>
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
export function StackSteps({ steps, deals, store }: StackStepsProps) {
  const { t } = useTranslation()
  const dealTypeLabel = useDealTypeLabel()
  const { data: clubs = [] } = useClubs()
  const [openStep, setOpenStep] = useState<number | null>(null)

  const activeStep = openStep === null ? null : (steps[openStep] ?? null)
  const activeDeal = activeStep ? (deals[activeStep.deal_id] ?? null) : null

  return (
    <>
      <ol className="space-y-1">
        {steps.map((step, index) => {
          const deal = deals[step.deal_id]
          const label = dealTypeLabel(deal?.deal_type)
          const clubLogo = getClubLogo(deal?.source_id, deal?.club_id)
          const clubName = resolveClubName(clubs, deal?.club_id, deal?.source_id)
          const isLast = index === steps.length - 1
          // A tender deal only discounts the slice of the bill routed through that
          // instrument; a price-level deal reports null and works off the whole bill.
          const isPartial = step.ils_covered !== null
          const discountBase = step.ils_covered ?? step.bill_before
          // What's still owed on a payment method. `bill_after` is the running
          // total you'll end up paying, so it keeps carrying the sum already
          // handed over on the covered slice — a 1,000 gift card bought for 700
          // against a 1,200 cart leaves it at 900. The bill itself only has 200
          // left to route anywhere, which is what `remaining_to_allocate` holds.
          // Price-level deals touch no instrument, so they stay on `bill_after`.
          const remainingAfter = step.remaining_to_allocate ?? step.bill_after
          const remainingBefore = isPartial
            ? (steps[index - 1]?.remaining_to_allocate ?? step.bill_before)
            : step.bill_before

          return (
            <li key={`${step.deal_id}-${index}`}>
              <div className="relative isolate overflow-hidden rounded-2xl bg-secondary p-3">
                {/* The club the deal comes from, watermarked across the block so a
                    stack can be scanned by brand at a glance. Decorative — the club is
                    already named in the row below — and `-z-10` inside the block's own
                    stacking context puts it above the fill but behind every bit of text.

                    Sized by height at its own aspect ratio (`h-full w-auto`) rather than
                    stretched to the block: the block goes from roughly 2:1 on a phone to
                    9:1 on a wide monitor, and forcing artwork to fill that either zooms
                    it to an unreadable crop or leaves it letterboxed. Centred, with the
                    gradient mask dissolving its own left and right edges so an opaque
                    card scan blends into the fill instead of reading as a pasted-on
                    rectangle — both physical properties, so RTL and LTR behave alike. */}
                {clubLogo ? (
                  <img
                    src={clubLogo.src}
                    alt=""
                    aria-hidden
                    loading="lazy"
                    className={cn(
                      "pointer-events-none absolute inset-y-0 left-1/2 -z-10 h-full w-auto max-w-full",
                      "-translate-x-1/2 select-none object-contain",
                      "[mask-image:linear-gradient(to_right,transparent,black_22%,black_78%,transparent)]",
                      clubLogo.tone === "dark" ? "opacity-[0.09]" : "opacity-[0.16]",
                    )}
                  />
                ) : null}

                <div className="flex items-start gap-3">
                  <span className="surface-teal flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold">
                    {index + 1}
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{deal?.title ?? step.deal_id}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {label ? <span className="rounded-md bg-card px-1.5 py-0.5 capitalize">{label}</span> : null}
                      {clubName ? <span>{clubName}</span> : null}
                    </div>
                  </div>

                  {/* The deal's own rate (`discount_rate`) — a share of the slice it
                      covered, not of the whole cart. A 30%-off gift card loaded with
                      1,000 against a 1,200 cart is a 30% deal; billing it as 25%
                      because 300 is a quarter of the cart misstates the offer people
                      are looking at. The trade-off is that the badges no longer share
                      a denominator, so they don't sum to the stack's headline saving —
                      the rows below carry the ILS each step actually took off. */}
                  <div className="shrink-0 text-end">
                    <span className="block rounded-xl bg-primary/10 px-2.5 py-1 text-sm font-bold text-primary">
                      {t("optimizer.stackSteps.percentOff", {
                        percent: formatPercent(step.discount_rate),
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
                    value={formatAmount(remainingAfter)}
                    was={formatAmount(remainingBefore)}
                  />
                </dl>

                {/* A tiered loadable card discounts at a rate that steps down as the
                    load grows. The badge above is the blend across those rungs, which
                    matches no single one of them, so the real rates are spelled out here. */}
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
