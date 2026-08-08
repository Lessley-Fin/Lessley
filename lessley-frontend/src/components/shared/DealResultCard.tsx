import { Calendar } from "lucide-react"
import { useTranslation } from "react-i18next"

import { emojiForCategory, formatCategoryLabel } from "@/lib/constants"
import { formatDate } from "@/lib/formatters"
import type { ClubDto, DealSearchResultItem } from "@/lib/types"
import { getClubName } from "@/lib/utils"

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

  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      className="w-full overflow-hidden rounded-3xl bg-card text-start shadow-[var(--shadow-card)] transition-transform active:scale-[0.99]"
    >
      <div className="surface-navy relative flex h-28 items-end p-4">
        <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-5xl opacity-40">
          {emojiForCategory(category)}
        </span>
        {rank !== undefined ? (
          <span className="absolute start-3 top-3 flex size-8 items-center justify-center rounded-full bg-card text-sm font-bold text-foreground">
            {rank}
          </span>
        ) : null}
        <div className="relative">
          <p className="text-sm font-bold">{store.name}</p>
          <p className="text-xs text-navy-muted">
            {category ? t(`categories.${category}`, { defaultValue: formatCategoryLabel(category) }) : t("dealFinder.card.deal")}
          </p>
        </div>
      </div>
      <div className="space-y-2 p-4">
        <p className="line-clamp-2 text-[15px] font-semibold">{deal.title}</p>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
            {getClubName(clubs, deal.clubId)}
          </span>
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Calendar className="size-3" aria-hidden />
            {formatDate(deal.scrapedAt)}
          </span>
        </div>
      </div>
    </button>
  )
}
