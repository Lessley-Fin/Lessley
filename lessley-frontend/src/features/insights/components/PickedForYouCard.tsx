import { Sparkles, Store } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { ListRow } from "@/components/shared/ListRow"
import { Card, CardContent } from "@/components/ui/card"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount, formatFitPercent } from "@/lib/formatters"
import type { ClubRecommendation, TopStoreInsight } from "@/lib/types"
import { getStoreLabel, getStoreTransactionCount, getStoreTotalAmount } from "../helpers"

interface PickedForYouCardProps {
  clubs: ClubRecommendation[]
  stores: TopStoreInsight[]
}

export function PickedForYouCard({ clubs, stores }: PickedForYouCardProps) {
  const topClubs = clubs.slice(0, INSIGHTS_DEFAULTS.TOP_CLUB_RECOMMENDATIONS_LIMIT)
  const topStores = stores.slice(0, INSIGHTS_DEFAULTS.TOP_STORES_LIMIT)
  const hasClubAnalysis = clubs.length > 0
  const topStoreTotalSpend = topStores.reduce((sum, store) => sum + getStoreTotalAmount(store), 0)

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={Sparkles}
        iconColor="violet"
        title="Picked for you"
        subtitle="Club fit vs. where you already shop"
      />
      <CardContent className="space-y-4 px-5 pb-5 pt-0">
        {!hasClubAnalysis ? (
          <p className="fintech-card-inset text-sm text-slate-600">
            We need more transaction history to analyze club fit. Try a longer time range or add more
            purchases through Open Banking.
          </p>
        ) : (
          <div className="space-y-2">
            <p className={fintech.sectionEyebrow}>Top 3 club matches</p>
            {topClubs.map((club, index) => (
              <ListRow key={club.club_id} variant="accent">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-slate-800">
                    {index + 1}. {club.club_name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatFitPercent(club.fit_score)} fit · {club.hit_count}/{club.total_stores} stores
                    match
                  </p>
                </div>
                <span className={fintech.fitBadge}>{formatFitPercent(club.fit_score)}</span>
              </ListRow>
            ))}
          </div>
        )}

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className={fintech.sectionEyebrow}>Top stores</p>
            {topStores.length ? (
              <p className={`${fintech.amount} text-xs`}>{formatAmount(topStoreTotalSpend)} total</p>
            ) : null}
          </div>
          {topStores.length ? (
            topStores.map((store, index) => (
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
            ))
          ) : (
            <p className="fintech-card-inset text-sm text-slate-600">
              No store patterns yet for this period.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
