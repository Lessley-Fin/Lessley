import { Calendar } from "lucide-react"
import { useTranslation } from "react-i18next"

import { DealImage } from "@/components/shared/DealImage"
import { DiscountBadge } from "@/components/shared/DiscountBadge"
import { track } from "@/features/interest/tracker"
import { useImpression } from "@/features/interest/useImpression"
import { emojiForCategory, formatCategoryLabel } from "@/lib/constants"
import { formatAmount, formatDate } from "@/lib/formatters"
import type { ClubDto, DealSearchResultItem } from "@/lib/types"
import { getClubName } from "@/lib/utils"

interface DealResultCardProps {
  item: DealSearchResultItem
  clubs: ClubDto[]
  rank?: number
  /** Which screen this card is on — recorded with every event it produces. */
  surface?: string
  /** 0-based rank in the list. Recorded so position debiasing can be added without a backfill. */
  position?: number
  onOpen: (item: DealSearchResultItem) => void
}

export function DealResultCard({ item, clubs, rank, surface, position, onOpen }: DealResultCardProps) {
  const { t } = useTranslation()
  const { deal, store } = item
  const category = store.metadata.mccCodes[0]
  const impressionRef = useImpression<HTMLButtonElement>("deal", deal.dealId, { surface, position })

  function handleOpen() {
    track("deal", deal.dealId, "open", { surface, position })
    track("store", store.storeId, "open", { surface, position })
    onOpen(item)
  }

  return (
    <button
      ref={impressionRef}
      type="button"
      onClick={handleOpen}
      className="w-full overflow-hidden rounded-3xl bg-card text-start shadow-[var(--shadow-card)] transition-transform active:scale-[0.99]"
    >
      {/* Scraped imagery is almost always a wide store logo, so it is contained
          on a light backdrop rather than cropped to fill — cover turns a logo
          into an unreadable slice. The category emoji stands in when there is
          no usable picture. */}
      <div className="relative h-28 bg-white">
        <DealImage
          urls={store.metadata.imageUrls}
          alt={store.name}
          className="absolute inset-0 h-full w-full"
          imageClassName="object-contain p-5"
          fallback={
            <span className="text-5xl opacity-30" aria-hidden>
              {emojiForCategory(category)}
            </span>
          }
        />

        {rank !== undefined ? (
          <span className="absolute start-3 top-3 flex size-8 items-center justify-center rounded-full bg-card text-sm font-bold text-foreground shadow-sm">
            {rank}
          </span>
        ) : null}
        <DiscountBadge discount={deal.discount} className="absolute end-3 top-3" />
      </div>

      <div className="space-y-2 p-4">
        <div>
          <p className="text-sm font-bold">{store.name}</p>
          <p className="text-xs text-muted-foreground">
            {category ? t(`categories.${category}`, { defaultValue: formatCategoryLabel(category) }) : t("dealFinder.card.deal")}
          </p>
        </div>
        <p className="line-clamp-2 text-[15px] font-semibold">{deal.title}</p>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
            {getClubName(clubs, deal.clubId)}
          </span>
          {deal.limits?.minimumPurchase ? (
            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
              {t("shared.discount.fromAmount", { amount: formatAmount(deal.limits.minimumPurchase) })}
            </span>
          ) : null}
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Calendar className="size-3" aria-hidden />
            {formatDate(deal.scrapedAt)}
          </span>
        </div>
      </div>
    </button>
  )
}
