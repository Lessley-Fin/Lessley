import { CheckCircle2, RefreshCw, TrendingDown } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { MissedSavingsList } from "@/components/shared/MissedSavingsList"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useClubs } from "@/features/clubs/hooks"
import type { TransactionInsight } from "@/lib/types"

const MISSED_OPPORTUNITIES_LIMIT = 5

interface MissedOpportunitiesCardProps {
  insights: TransactionInsight[]
  onTrigger: () => void
  isPending: boolean
  isSuccess: boolean
}

export function MissedOpportunitiesCard({ insights, onTrigger, isPending, isSuccess }: MissedOpportunitiesCardProps) {
  const { data: clubs = [] } = useClubs()

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={TrendingDown}
        iconColor="amber"
        title="Missed Opportunities"
        subtitle="Where you could have saved"
      />
      <CardContent className="space-y-3 px-5 pb-5 pt-0">
        <MissedSavingsList items={insights} clubs={clubs} limit={MISSED_OPPORTUNITIES_LIMIT} />

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
            {isPending ? "Analyzing…" : "Analyze missed savings"}
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
