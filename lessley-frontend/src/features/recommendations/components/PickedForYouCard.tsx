import { Sparkles } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { ListRow } from "@/components/shared/ListRow"
import { Card, CardContent } from "@/components/ui/card"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { formatFitPercent } from "@/lib/formatters"
import type { ClubRecommendation } from "@/lib/types"

interface PickedForYouCardProps {
  clubs: ClubRecommendation[]
}

export function PickedForYouCard({ clubs }: PickedForYouCardProps) {
  const topClubs = clubs.slice(0, INSIGHTS_DEFAULTS.TOP_CLUB_RECOMMENDATIONS_LIMIT)
  const hasClubAnalysis = clubs.length > 0

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={Sparkles}
        iconColor="violet"
        title="Picked for you"
        subtitle="Club fit based on your spending"
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
      </CardContent>
    </Card>
  )
}
