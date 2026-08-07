import { useState } from "react"

import { CarouselDots } from "@/components/shared/CarouselDots"
import { Carousel, CarouselContent, CarouselItem, type CarouselApi } from "@/components/ui/carousel"
import { useMyProfile } from "@/features/user/hooks"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { AccountsSlide } from "./components/AccountsSlide"
import { AnalysisPeriodCard } from "./components/AnalysisPeriodCard"
import { ConnectBankCard } from "./components/ConnectBankCard"
import { ConnectionCheck } from "./components/ConnectionCheck"
import { RecentTransactionsSlide } from "./components/RecentTransactionsSlide"
import { SavingsHeroCard } from "./components/SavingsHeroCard"
import { SpendingOverviewSlide } from "./components/SpendingOverviewSlide"
import { StatsGridCard } from "./components/StatsGridCard"
import { TopCategorySlide } from "./components/TopCategorySlide"
import { TopStoresSlide } from "./components/TopStoresSlide"
import {
  useCategoryInsights,
  useHasConnection,
  useInitOpenFinance,
  useSpendingPeriodComparison,
  useSpendingSaved,
  useTopAccounts,
  useTopStores,
  useTransactions,
} from "./hooks"

const CAROUSEL_LABELS = ["Overview", "Categories", "Top stores", "Transactions", "Accounts"]

function periodLabelFor(days: number) {
  return days === 365 ? "last year" : `last ${days} days`
}

export function InsightsRecommendationsPage() {
  const [timeRangeDays, setTimeRangeDays] = useState<number>(INSIGHTS_DEFAULTS.DEFAULT_TIME_RANGE_DAYS)
  const [deepDiveDays, setDeepDiveDays] = useState<number>(INSIGHTS_DEFAULTS.DEFAULT_TIME_RANGE_DAYS)
  const [carouselApi, setCarouselApi] = useState<CarouselApi>()

  const { data: isConnected, isLoading: checkingConnection } = useHasConnection()
  const connected = isConnected === true

  const { data: profile } = useMyProfile()

  const { data: transactions = [], isLoading: txLoading, error: txError } = useTransactions(timeRangeDays, connected)
  const { data: spendingSaved = null } = useSpendingSaved(timeRangeDays, connected)
  const { data: linkedAccounts = [] } = useTopAccounts(timeRangeDays, connected)

  const {
    data: deepDiveTransactions = [],
    isLoading: deepDiveLoading,
    error: deepDiveError,
  } = useTransactions(deepDiveDays, connected)
  const { data: categoryInsights = [] } = useCategoryInsights(deepDiveDays, connected)
  const { data: deepDiveAccounts = [] } = useTopAccounts(deepDiveDays, connected)
  const { data: topStoresRaw = [] } = useTopStores(deepDiveDays, connected)
  const { data: spendingComparison = null } = useSpendingPeriodComparison(deepDiveDays, connected)

  const initOpenFinance = useInitOpenFinance()

  const insightsError = txError instanceof Error ? txError.message : ""
  const deepDiveErrorMessage = deepDiveError instanceof Error ? deepDiveError.message : ""

  const totalSpend = transactions.reduce((sum, tx) => {
    const amount = tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount
    return sum + (typeof amount === "number" ? amount : 0)
  }, 0)

  const periodLabel = periodLabelFor(timeRangeDays)
  const deepDivePeriodLabel = periodLabelFor(deepDiveDays)

  function handleConnectOpenBanking() {
    initOpenFinance.mutate(undefined, {
      onSuccess: (data) => {
        window.location.assign(data.connectUrl)
      },
    })
  }

  if (checkingConnection) {
    return <ConnectionCheck />
  }

  if (!connected) {
    return (
      <ConnectBankCard
        onConnect={handleConnectOpenBanking}
        isPending={initOpenFinance.isPending}
        error={initOpenFinance.error}
      />
    )
  }

  return (
    <div className="space-y-6 pb-2">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Your money, decoded</h1>
        <p className="text-sm text-muted-foreground">
          {periodLabel.charAt(0).toUpperCase() + periodLabel.slice(1)} · {linkedAccounts.length} linked accounts
        </p>
      </div>

      <AnalysisPeriodCard value={timeRangeDays} onChange={setTimeRangeDays} />

      {txLoading ? (
        <p className="text-sm text-muted-foreground">Loading insights...</p>
      ) : insightsError ? (
        <p className="text-sm text-destructive">{insightsError}</p>
      ) : (
        <>
          <SavingsHeroCard
            totalSaved={spendingSaved?.total_saved ?? 0}
            periodLabel={periodLabel}
            clubsCount={profile?.clubs?.length ?? 0}
          />
          <StatsGridCard transactionCount={transactions.length} totalAmount={totalSpend} periodLabel={periodLabel} />
        </>
      )}

      <div className="space-y-3 border-t border-border/70 pt-5">
        <div>
          <h2 className="text-lg font-bold tracking-tight">Deep dive</h2>
          <p className="text-sm text-muted-foreground">
            Swipe through the details for the {deepDivePeriodLabel}.
          </p>
        </div>

        <AnalysisPeriodCard value={deepDiveDays} onChange={setDeepDiveDays} />

        {deepDiveLoading ? (
          <p className="text-sm text-muted-foreground">Loading insights...</p>
        ) : deepDiveErrorMessage ? (
          <p className="text-sm text-destructive">{deepDiveErrorMessage}</p>
        ) : (
          <>
            <Carousel setApi={setCarouselApi} opts={{ align: "start" }}>
              <CarouselContent>
                <CarouselItem>
                  <SpendingOverviewSlide comparison={spendingComparison} />
                </CarouselItem>
                <CarouselItem>
                  <TopCategorySlide categories={categoryInsights} />
                </CarouselItem>
                <CarouselItem>
                  <TopStoresSlide stores={topStoresRaw} />
                </CarouselItem>
                <CarouselItem>
                  <RecentTransactionsSlide transactions={deepDiveTransactions} />
                </CarouselItem>
                <CarouselItem>
                  <AccountsSlide accounts={deepDiveAccounts} />
                </CarouselItem>
              </CarouselContent>
            </Carousel>
            <CarouselDots api={carouselApi} labels={CAROUSEL_LABELS} />
          </>
        )}
      </div>
    </div>
  )
}
