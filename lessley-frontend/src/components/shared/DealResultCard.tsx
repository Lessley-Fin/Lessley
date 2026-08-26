import { Calendar } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ClubLogoTile } from "@/components/shared/ClubLogoTile"
import { DealImage } from "@/components/shared/DealImage"
import { DiscountBadge } from "@/components/shared/DiscountBadge"
import { emojiForCategory, formatCategoryLabel } from "@/lib/constants"
import { formatAmount, formatDate } from "@/lib/formatters"
import { resolveClubName } from "@/lib/clubs"
import type { ClubDto, DealSearchResultItem } from "@/lib/types"

interface DealResultCardProps {
  item: DealSearchResultItem
  clubs: ClubDto[]
  rank?: number
  onOpen: (item: DealSearchResultItem) => void
}

export function DealResultCard({ item, clubs, rank, onOpen }: DealResultCardProps) {
  const { t } = useTranslation()
  const { deal, store } = item
  const category = store.metadata.mccCodes[0]
  const clubName = resolveClubName(clubs, deal.clubId)

  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
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
          {clubName ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary py-0.5 pe-2.5 ps-1 text-xs font-medium text-secondary-foreground">
              <ClubLogoTile clubId={deal.clubId} clubName={clubName} variant="inline" />
              {clubName}
            </span>
          ) : null}
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
