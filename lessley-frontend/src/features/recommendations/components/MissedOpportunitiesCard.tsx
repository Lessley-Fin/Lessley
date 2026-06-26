import { CheckCircle2, Lightbulb, RefreshCw, Store, TrendingDown } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { CLUBS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount } from "@/lib/formatters"
import type { TransactionInsight } from "@/lib/types"

const MISSED_OPPORTUNITIES_LIMIT = 5

function resolveClubName(clubId: string): string {
  return CLUBS.find((c) => c.id === clubId)?.name ?? clubId
}

interface MissedOpportunitiesCardProps {
  insights: TransactionInsight[]
  onTrigger: () => void
  isPending: boolean
  isSuccess: boolean
}

export function MissedOpportunitiesCard({ insights, onTrigger, isPending, isSuccess }: MissedOpportunitiesCardProps) {
  const relevantInsights = insights
    .filter((i) => i.missed_store_discont.length > 0)
    .slice(0, MISSED_OPPORTUNITIES_LIMIT)

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={TrendingDown}
        iconColor="amber"
        title="Missed Opportunities"
        subtitle="Where you could have saved"
      />
      <CardContent className="space-y-3 px-5 pb-5 pt-0">
        {relevantInsights.length === 0 ? (
          <p className="fintech-card-inset text-sm text-slate-600">
            No missed savings data yet. Once your spending is analyzed, we'll show you where you could
            have saved.
          </p>
        ) : (
          relevantInsights.map((insight) => {
            const topDiscount = insight.missed_store_discont[0]
            const clubName = topDiscount ? resolveClubName(topDiscount.club_id) : null
            const altStoreNames = topDiscount?.missed_store
              .slice(0, 3)
              .map((s) => s.store_name)
              .join(", ")
            const extraClubs = insight.missed_store_discont.length - 1

            return (
              <div
                key={insight.transaction_id}
                className="space-y-2 rounded-2xl border border-slate-100 bg-slate-50/60 p-4"
              >
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
                    <Store className="size-3.5" />
                  </div>
                  <p className="text-sm font-medium text-slate-800">
                    You spent {formatAmount(insight.amount)} at {insight.store_name}
                  </p>
                </div>

                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-lg bg-red-100 text-red-500">
                    <TrendingDown className="size-3.5" />
                  </div>
                  <p className="text-sm text-slate-600">
                    Savings were available in{" "}
                    <span className="font-medium text-slate-700">{insight.mcc_description}</span>
                  </p>
                </div>

                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
                    <Lightbulb className="size-3.5" />
                  </div>
                  <div className="min-w-0 text-sm text-slate-600">
                    <p>
                      <span className="font-medium text-slate-700">{clubName}</span> had deals at{" "}
                      {altStoreNames}
                    </p>
                    {extraClubs > 0 ? (
                      <p className={`${fintech.sectionEyebrow} mt-0.5`}>
                        +{extraClubs} more club{extraClubs !== 1 ? "s" : ""} with deals
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>
            )
          })
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
