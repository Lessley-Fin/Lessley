import { useState } from "react"
import { Flame } from "lucide-react"
import { useTranslation } from "react-i18next"

import { DealDetailDialog } from "@/components/shared/DealDetailDialog"
import { DealResultCard } from "@/components/shared/DealResultCard"
import { InfoDialog } from "@/components/shared/InfoDialog"
import { useClubs } from "@/features/clubs/hooks"
import { useDealSearch } from "@/features/deal-finder/hooks"
import type { DealSearchResultItem } from "@/lib/types"

// No popularity/search-interest data exists in the backend, so this can't be a real "trending"
// feed — it's a fixed, broad category slice of real deals, honestly framed as "featured" rather
// than ranked by interest.
const FEATURED_CATEGORIES = ["GROCERIES", "RESTAURANT", "ELECTRONICS", "CLOTHES_&_ACCESSORIES", "COFFEE_&_SNACKS", "CAR_&_FUEL"]

export function HotDealsPage() {
  const { t } = useTranslation()
  const [openItem, setOpenItem] = useState<DealSearchResultItem | null>(null)
  const { data: clubs = [] } = useClubs()
  const { data, isLoading, error } = useDealSearch(
    { mccCodes: FEATURED_CATEGORIES, storeText: "", dealText: "", page: 1, pageSize: 10 },
    true
  )

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            {t("dealFinder.hotDeals.title")}
            <Flame className="size-6 text-warning" aria-hidden />
          </h1>
          <p className="text-sm text-muted-foreground">{t("dealFinder.hotDeals.subtitle")}</p>
        </div>
        <InfoDialog
          ariaLabel={t("dealFinder.hotDeals.infoDialog.ariaLabel")}
          title={t("dealFinder.hotDeals.infoDialog.title")}
        >
          <p className="text-sm text-muted-foreground">{t("dealFinder.hotDeals.infoDialog.body")}</p>
        </InfoDialog>
      </div>

      <div className="no-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto pb-2">
        {isLoading ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            {t("dealFinder.hotDeals.loading")}
          </p>
        ) : error ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-destructive shadow-[var(--shadow-card)]">
            {error instanceof Error ? error.message : t("dealFinder.hotDeals.loadFailed")}
          </p>
        ) : data && data.items.length === 0 ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            {t("dealFinder.hotDeals.empty")}
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
