import { useEffect, useState } from "react"
import { Lightbulb } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"

import { Carousel, CarouselContent, CarouselItem, type CarouselApi } from "@/components/ui/carousel"
import { useClubs } from "@/features/clubs/hooks"
import { ConnectionCheck } from "@/features/insights/components/ConnectionCheck"
import {
  useHasConnection,
  useRecommendations,
  useTriggerMatchingClubs,
  useTriggerMissedSavings,
} from "@/features/insights/hooks"
import { getDirection } from "@/lib/i18n/config"
import { queryKeys } from "@/lib/query-keys"
import type { ClubRecommendation, ClubRecommendationResponse, TransactionInsight } from "@/lib/types"
import { cn } from "@/lib/utils"
import { MissedSavingsSlide } from "./components/MissedSavingsSlide"
import { TopClubMatchesSlide } from "./components/TopClubMatchesSlide"

export function RecommendationsPage() {
  const { t, i18n } = useTranslation()
  const direction = getDirection(i18n.language)
  const TABS = [t("recommendations.page.tabTopMatches"), t("recommendations.page.tabMissedSavings")]
  const queryClient = useQueryClient()
  const [api, setApi] = useState<CarouselApi>()
  const [selected, setSelected] = useState(0)

  const { data: isConnected, isLoading: checkingConnection } = useHasConnection()
  const connected = isConnected === true

  const { data: clubs = [] } = useClubs()
  const { data: recommendationsData } = useRecommendations(connected)

  const triggerMatchingClubs = useTriggerMatchingClubs()
  const triggerMissedSavings = useTriggerMissedSavings()

  useEffect(() => {
    if (!api) return
    const onSelect = () => setSelected(api.selectedScrollSnap())
    onSelect()
    api.on("select", onSelect)
    return () => {
      api.off("select", onSelect)
    }
  }, [api])

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
    return <ConnectionCheck />
  }

  if (!connected) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-3xl bg-card p-8 text-center shadow-[var(--shadow-card)]">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-accent">
          <Lightbulb className="size-6 text-accent-foreground" aria-hidden />
        </div>
        <p className="font-bold">{t("recommendations.page.notConnectedTitle")}</p>
        <p className="text-sm text-muted-foreground">{t("recommendations.page.notConnectedSubtitle")}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4 pb-2">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("recommendations.page.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("recommendations.page.subtitle")}</p>
      </div>

      <div className="flex gap-1 rounded-full border border-border bg-card p-1">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            type="button"
            onClick={() => api?.scrollTo(i)}
            className={cn(
              "flex-1 rounded-full py-2 text-sm font-semibold transition-colors",
              selected === i ? "surface-teal shadow-[var(--shadow-card)]" : "text-muted-foreground",
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      <Carousel setApi={setApi} opts={{ align: "start", direction }}>
        <CarouselContent>
          <CarouselItem>
            <TopClubMatchesSlide
              clubs={clubRecommendations}
              onRecalculate={handleTriggerMatchingClubs}
              isPending={triggerMatchingClubs.isPending}
            />
          </CarouselItem>
          <CarouselItem>
            <MissedSavingsSlide
              insights={missedSavings}
              clubs={clubs}
              onRecalculate={handleTriggerMissedSavings}
              isPending={triggerMissedSavings.isPending}
            />
          </CarouselItem>
        </CarouselContent>
      </Carousel>
    </div>
  )
}
