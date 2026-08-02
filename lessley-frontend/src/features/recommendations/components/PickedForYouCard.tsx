import { CheckCircle2, RefreshCw, Sparkles } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { MatchingClubsList } from "@/components/shared/MatchingClubsList"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import type { ClubRecommendation } from "@/lib/types"

interface PickedForYouCardProps {
  clubs: ClubRecommendation[]
  onTrigger: () => void
  isPending: boolean
  isSuccess: boolean
}

export function PickedForYouCard({ clubs, onTrigger, isPending, isSuccess }: PickedForYouCardProps) {
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
        {hasClubAnalysis ? (
          <>
            <p className={fintech.sectionEyebrow}>Top 3 club matches</p>
            <MatchingClubsList clubs={clubs} limit={INSIGHTS_DEFAULTS.TOP_CLUB_RECOMMENDATIONS_LIMIT} />
          </>
        ) : (
          <p className="fintech-card-inset text-sm text-slate-600">
            We need more transaction history to analyze club fit. Try a longer time range or add more
            purchases through Open Banking.
          </p>
        )}

        <div className="flex items-center gap-3 pt-1">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={onTrigger}
            disabled={isPending}
          >
            <RefreshCw className={`size-3.5 ${isPending ? "animate-spin" : ""}`} />
            {isPending ? "Calculating…" : "Calculate matching clubs"}
          </Button>
          {isSuccess ? (
            <span className="flex items-center gap-1 text-xs text-emerald-600">
              <CheckCircle2 className="size-3.5" />
              Started — check back soon
            </span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}
