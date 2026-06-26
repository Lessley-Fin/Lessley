import { Lightbulb } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"

import { EmptyState } from "@/components/shared/EmptyState"
import { ConnectionCheck } from "@/features/insights/components/ConnectionCheck"
import {
  useHasConnection,
  useRecommendations,
  useTriggerMatchingClubs,
  useTriggerMissedSavings,
} from "@/features/insights/hooks"
import { queryKeys } from "@/lib/query-keys"
import { fintech } from "@/lib/fintech-styles"
import type { ClubRecommendation, ClubRecommendationResponse, TransactionInsight } from "@/lib/types"
import { MissedOpportunitiesCard } from "./components/MissedOpportunitiesCard"
import { PickedForYouCard } from "./components/PickedForYouCard"

export function RecommendationsPage() {
  const queryClient = useQueryClient()
  const { data: isConnected, isLoading: checkingConnection } = useHasConnection()
  const connected = isConnected === true

  const { data: recommendationsData } = useRecommendations(connected)

  const triggerMatchingClubs = useTriggerMatchingClubs()
  const triggerMissedSavings = useTriggerMissedSavings()

  const clubData = recommendationsData?.matchingClubs?.data as ClubRecommendationResponse | null | undefined
  const clubRecommendations: ClubRecommendation[] = clubData?.recommendations ?? []

  const missedSavingsData = recommendationsData?.missedSavings?.data as TransactionInsight[] | null | undefined
  const missedSavings: TransactionInsight[] = Array.isArray(missedSavingsData) ? missedSavingsData : []

  function handleTriggerMatchingClubs() {
    triggerMatchingClubs.mutate(undefined, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.recommendations.list() })
      },
    })
  }

  function handleTriggerMissedSavings() {
    triggerMissedSavings.mutate(undefined, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.recommendations.list() })
      },
    })
  }

  if (checkingConnection) {
    return (
      <section className={fintech.page}>
        <ConnectionCheck />
      </section>
    )
  }

  if (!connected) {
    return (
      <section className={fintech.page}>
        <EmptyState
          icon={Lightbulb}
          title="Connect to get recommendations"
          description="Link your bank account from the Insights tab to unlock personalized recommendations and savings analysis."
        />
      </section>
    )
  }

  return (
    <section className={fintech.page}>
      <PickedForYouCard
        clubs={clubRecommendations}
        onTrigger={handleTriggerMatchingClubs}
        isPending={triggerMatchingClubs.isPending}
        isSuccess={triggerMatchingClubs.isSuccess}
      />
      <MissedOpportunitiesCard
        insights={missedSavings}
        onTrigger={handleTriggerMissedSavings}
        isPending={triggerMissedSavings.isPending}
        isSuccess={triggerMissedSavings.isSuccess}
      />
    </section>
  )
}
