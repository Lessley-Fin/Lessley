import { ExternalLink } from "lucide-react"
import { useTranslation } from "react-i18next"

import { DealImage } from "@/components/shared/DealImage"
import { DealTerms } from "@/components/shared/DealTerms"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { formatAmount } from "@/lib/formatters"
import type { OptimizerDealSummary, OptimizerStep, OptimizerStore } from "@/lib/types"

interface DealInfoDialogProps {
  deal: OptimizerDealSummary | null
  /** The step this deal produced, so the terms sit next to the actual numbers. */
  step: OptimizerStep | null
  /** The store the cart was priced at — deals carry no imagery of their own. */
  store?: OptimizerStore | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function useDealTypeLabel() {
  const { t } = useTranslation()
  return (dealType?: string | null) =>
    dealType ? t(`shared.dealTypes.${dealType}`, { defaultValue: dealType.replace(/_/g, " ") }) : null
}

export function DealInfoDialog({ deal, step, store, open, onOpenChange }: DealInfoDialogProps) {
  const { t } = useTranslation()
  const dealTypeLabel = useDealTypeLabel()

  const typeLabel = dealTypeLabel(deal?.deal_type)
  const storeImages = store?.image_urls ?? []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[340px] rounded-3xl">
        {deal ? (
          <>
            <DialogHeader>
              <DialogTitle className="text-start text-base">{deal.title ?? deal.deal_id}</DialogTitle>
              <DialogDescription className="text-start">
                {[typeLabel, deal.source_id].filter(Boolean).join(" · ") || t("optimizer.dealInfo.deal")}
              </DialogDescription>
            </DialogHeader>

            <DialogBody>
              {deal.description && deal.description !== deal.title ? (
                <p className="text-sm text-muted-foreground">{deal.description}</p>
              ) : null}

              {/* What this deal did to *this* cart — the terms below explain these numbers. */}
              {step ? (
                <div className="space-y-1 rounded-2xl bg-secondary p-3 text-sm">
                  <Row
                    label={t("optimizer.stackSteps.discountAppliesTo")}
                    value={formatAmount(step.ils_covered ?? step.bill_before)}
                  />
                  {step.ils_covered !== null ? (
                    <Row
                      label={t("optimizer.stackSteps.youPayOnIt")}
                      value={formatAmount(step.amount_paid_on_covered)}
                    />
                  ) : null}
                  <Row
                    label={t("optimizer.dealInfo.savedHere")}
                    value={`−${formatAmount(step.savings)}`}
                    accent
                  />
                </div>
              ) : null}

              <DealTerms
                minimumPurchase={deal.minimum_purchase}
                maxDiscountAmount={deal.max_discount_amount}
                maxUsesPerTransaction={deal.max_uses_per_transaction}
                maxUsesPerMonth={deal.max_uses_per_month}
                membershipRequired={deal.membership_required}
                membershipSource={deal.source_id}
                fineprint={deal.terms_and_conditions}
              />

              {/* Deals have no imagery of their own — these are the store's, which is
                  what the pipeline attaches every picture it scrapes alongside a deal to. */}
              {storeImages.length > 0 ? (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {storeImages.map((url, index) => (
                    <DealImage
                      key={`${url}-${index}`}
                      urls={[url]}
                      alt={store?.name ?? deal.title ?? deal.deal_id}
                      className="h-20 w-28 shrink-0 rounded-xl bg-white"
                      imageClassName="object-contain p-2"
                      fallback={null}
                    />
                  ))}
                </div>
              ) : null}
            </DialogBody>

            <DialogFooter>
              {deal.url ? (
                <Button asChild variant="hero" size="xl">
                  <a href={deal.url} target="_blank" rel="noopener noreferrer">
                    {t("optimizer.dealInfo.openDeal")}
                  </a>
                </Button>
              ) : null}

              {deal.store_url && deal.store_url !== deal.url ? (
                <a
                  href={deal.store_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-1 text-xs font-medium text-primary"
                >
                  <ExternalLink className="size-3" aria-hidden />
                  {t("optimizer.dealInfo.visitStore")}
                </a>
              ) : null}
            </DialogFooter>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function Row({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className={accent ? "font-semibold text-primary" : "font-semibold"}>{value}</span>
    </div>
  )
}
