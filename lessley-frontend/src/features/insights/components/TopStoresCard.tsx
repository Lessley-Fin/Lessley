import { Store } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { ListRow } from "@/components/shared/ListRow"
import { Card, CardContent } from "@/components/ui/card"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount } from "@/lib/formatters"
import type { TopStoreInsight } from "@/lib/types"
import { getStoreLabel, getStoreTransactionCount, getStoreTotalAmount } from "../helpers"

interface TopStoresCardProps {
  stores: TopStoreInsight[]
}

export function TopStoresCard({ stores }: TopStoresCardProps) {
  const topStores = stores.slice(0, INSIGHTS_DEFAULTS.TOP_STORES_LIMIT)
  const topStoreTotalSpend = topStores.reduce((sum, store) => sum + getStoreTotalAmount(store), 0)

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={Store}
        iconColor="violet"
        title="Top stores"
        subtitle="Where you spend the most"
      />
      <CardContent className="space-y-2 px-5 pb-5 pt-0">
        {topStores.length ? (
          <>
            <div className="flex items-center justify-between gap-2">
              <p className={fintech.sectionEyebrow}>{topStores.length} stores</p>
              <p className={`${fintech.amount} text-xs`}>{formatAmount(topStoreTotalSpend)} total</p>
            </div>
            {topStores.map((store, index) => (
              <ListRow key={`${getStoreLabel(store)}-${index}`}>
                <span className={fintech.rankBadge}>{index + 1}</span>
                <div className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-violet-100 text-violet-600">
                  <Store className="size-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-slate-800">{getStoreLabel(store)}</p>
                  <p className="text-xs text-slate-500">
                    {getStoreTransactionCount(store)} purchases
                  </p>
                </div>
                <p className={`${fintech.amount} shrink-0 text-sm`}>
                  {formatAmount(getStoreTotalAmount(store))}
                </p>
              </ListRow>
            ))}
          </>
        ) : (
          <p className="fintech-card-inset text-sm text-slate-600">
            No store patterns yet for this period.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
