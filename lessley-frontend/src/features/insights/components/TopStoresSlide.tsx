import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { INSIGHTS_DEFAULTS, emojiForStore } from "@/lib/constants"
import { formatAmount } from "@/lib/formatters"
import type { TopStoreInsight } from "@/lib/types"
import { getStoreLabel, getStoreTransactionCount, getStoreTotalAmount } from "../helpers"

interface TopStoresSlideProps {
  stores: TopStoreInsight[]
}

export function TopStoresSlide({ stores }: TopStoresSlideProps) {
  const topStores = stores.slice(0, INSIGHTS_DEFAULTS.CAROUSEL_LIST_LIMIT)

  if (topStores.length === 0) {
    return (
      <CarouselSlideCard title="Top stores" subtitle="Scroll for the full ten">
        <p className="text-sm text-muted-foreground">No store patterns yet for this period.</p>
      </CarouselSlideCard>
    )
  }

  return (
    <CarouselSlideCard title="Top stores" subtitle="Scroll for the full ten">
      <ul className="no-scrollbar max-h-52 space-y-2 overflow-y-auto pr-1">
        {topStores.map((store, i) => {
          const label = getStoreLabel(store)
          return (
            <li key={`${label}-${i}`} className="flex items-center gap-3 rounded-2xl bg-secondary p-3">
              <span className="flex size-8 items-center justify-center rounded-full bg-card text-sm">
                {emojiForStore(label)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">
                  {i + 1}. {label}
                </p>
                <p className="text-xs text-muted-foreground">{getStoreTransactionCount(store)} transactions</p>
              </div>
              <span className="text-sm font-bold">{formatAmount(getStoreTotalAmount(store))}</span>
            </li>
          )
        })}
      </ul>
    </CarouselSlideCard>
  )
}
