import { useState } from "react"
import { Flame } from "lucide-react"

import { DealDetailDialog } from "@/components/shared/DealDetailDialog"
import { DealResultCard } from "@/components/shared/DealResultCard"
import { useClubs } from "@/features/clubs/hooks"
import { useDealSearch } from "@/features/deal-finder/hooks"
import type { DealSearchResultItem } from "@/lib/types"

// No popularity/search-interest data exists in the backend, so this can't be a real "trending"
// feed — it's a fixed, broad category slice of real deals, honestly framed as "featured" rather
// than ranked by interest.
const FEATURED_CATEGORIES = ["GROCERIES", "RESTAURANT", "ELECTRONICS", "CLOTHES_&_ACCESSORIES", "COFFEE_&_SNACKS", "CAR_&_FUEL"]

export function HotDealsPage() {
  const [openItem, setOpenItem] = useState<DealSearchResultItem | null>(null)
  const { data: clubs = [] } = useClubs()
  const { data, isLoading, error } = useDealSearch(
    { mccCodes: FEATURED_CATEGORIES, storeText: "", dealText: "", page: 1, pageSize: 10 },
    true
  )

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          Featured deals
          <Flame className="size-6 text-warning" aria-hidden />
        </h1>
        <p className="text-sm text-muted-foreground">Real deals across your loyalty clubs, refreshed regularly</p>
      </div>

      <div className="no-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto pb-2">
        {isLoading ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            Loading deals…
          </p>
        ) : error ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-destructive shadow-[var(--shadow-card)]">
            {error instanceof Error ? error.message : "Failed to load deals."}
          </p>
        ) : data && data.items.length === 0 ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            No featured deals right now — check back soon.
          </p>
        ) : (
          data?.items.map((item, index) => (
            <DealResultCard key={item.deal.dealId} item={item} clubs={clubs} rank={index + 1} onOpen={setOpenItem} />
          ))
        )}
      </div>

      <DealDetailDialog item={openItem} clubs={clubs} onOpenChange={(open) => !open && setOpenItem(null)} />
    </div>
  )
}
