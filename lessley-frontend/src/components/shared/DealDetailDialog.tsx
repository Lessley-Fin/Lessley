import { useState } from "react"
import { Check, Copy, ExternalLink } from "lucide-react"
import { useTranslation } from "react-i18next"

import { DealTerms } from "@/components/shared/DealTerms"
import { DiscountBadge } from "@/components/shared/DiscountBadge"
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
import { emojiForCategory, formatCategoryLabel } from "@/lib/constants"
import { formatDate } from "@/lib/formatters"
import type { ClubDto, DealSearchResultItem } from "@/lib/types"
import { getClubName } from "@/lib/utils"

interface DealDetailDialogProps {
  item: DealSearchResultItem | null
  clubs: ClubDto[]
  onOpenChange: (open: boolean) => void
}

export function DealDetailDialog({ item, clubs, onOpenChange }: DealDetailDialogProps) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)

  function handleCopyCode(code: string) {
    void navigator.clipboard.writeText(code)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  const category = item?.store.metadata.mccCodes[0]

  return (
    <Dialog open={!!item} onOpenChange={onOpenChange}>
      {/* The deal is the densest thing we put in a dialog — title, badge row,
          terms, coupon and an image strip — so it gets a wider, taller box than
          the max-w-sm default. On a phone it's still the full-bleed width the
          base sets; the extra room only shows up once the screen has it. */}
      <DialogContent className="max-w-md sm:max-h-[75dvh] sm:max-w-md">
        {item ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <span className="shrink-0 text-xl xs:text-2xl" aria-hidden>
                  {emojiForCategory(category)}
                </span>
                <span className="min-w-0">{item.store.name}</span>
              </DialogTitle>
              <DialogDescription>
                {category ? t(`categories.${category}`, { defaultValue: formatCategoryLabel(category) }) : t("dealFinder.detailDialog.deal")}
              </DialogDescription>
            </DialogHeader>

            <DialogBody>
              <p className="text-[15px] font-semibold sm:text-base">{item.deal.title}</p>
              {item.deal.description && item.deal.description !== item.deal.title ? (
                <p className="text-sm text-muted-foreground sm:text-[15px]">{item.deal.description}</p>
              ) : null}

              <div className="flex flex-wrap items-center gap-2">
                <DiscountBadge discount={item.deal.discount} />
                <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
                  {getClubName(clubs, item.deal.clubId)}
                </span>
                {item.deal.dealType ? (
                  <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium capitalize text-secondary-foreground">
                    {t(`shared.dealTypes.${item.deal.dealType}`, {
                      defaultValue: item.deal.dealType.replace(/_/g, " "),
                    })}
                  </span>
                ) : null}
                <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
                  {t("dealFinder.detailDialog.scraped", { date: formatDate(item.deal.scrapedAt) })}
                </span>
              </div>

              <DealTerms
                minimumPurchase={item.deal.limits?.minimumPurchase}
                minSpend={item.deal.discount?.minSpend}
                maxDiscountAmount={item.deal.discount?.maxDiscountAmount}
                maxUsesPerTransaction={item.deal.limits?.maxUsesPerTransaction}
                maxUsesPerMonth={item.deal.limits?.maxUsesPerMonth}
                membershipRequired={item.deal.membershipRequired}
                redeemChannels={item.deal.redeemChannels}
                fineprint={item.deal.termsAndConditions}
              />

              {item.deal.couponCode ? (
                <div className="flex items-center gap-2 rounded-xl border border-dashed border-border bg-secondary px-3 py-2">
                  <span className="flex-1 font-mono text-sm font-semibold">{item.deal.couponCode}</span>
                  <button
                    type="button"
                    onClick={() => handleCopyCode(item.deal.couponCode!)}
                    className="shrink-0 text-xs font-medium text-primary"
                    aria-label={t("dealFinder.detailDialog.copyCouponAria")}
                  >
                    {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                  </button>
                </div>
              ) : null}

              {item.store.metadata.imageUrls.length > 0 ? (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {item.store.metadata.imageUrls.map((url, i) => (
                    <img
                      key={url + i}
                      src={url}
                      alt={`${item.store.name} ${i + 1}`}
                      className="h-16 w-24 shrink-0 rounded-xl bg-white object-contain p-2 xs:h-20 xs:w-28 sm:h-24 sm:w-32"
                      onError={(e) => {
                        ;(e.target as HTMLImageElement).style.display = "none"
                      }}
                    />
                  ))}
                </div>
              ) : null}
            </DialogBody>

            <DialogFooter>
              {item.deal.benefitUrl ? (
                <Button asChild variant="hero" size="xl">
                  <a href={item.deal.benefitUrl} target="_blank" rel="noopener noreferrer">
                    {t("dealFinder.detailDialog.getThisDeal")}
                  </a>
                </Button>
              ) : null}

              {item.store.metadata.storeUrl ? (
                <a
                  href={item.store.metadata.storeUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-1 text-xs font-medium text-primary"
                >
                  <ExternalLink className="size-3" aria-hidden />
                  {t("dealFinder.detailDialog.visitStore")}
                </a>
              ) : null}
            </DialogFooter>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
