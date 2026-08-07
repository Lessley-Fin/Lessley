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
import { TrueCostSlide } from "./components/TrueCostSlide"
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

const CAROUSEL_LABELS = ["Overview", "Categories", "True cost", "Top stores", "Transactions", "Accounts"]

export function InsightsRecommendationsPage() {
  const [timeRangeDays, setTimeRangeDays] = useState<number>(INSIGHTS_DEFAULTS.DEFAULT_TIME_RANGE_DAYS)
  const [carouselApi, setCarouselApi] = useState<CarouselApi>()

  const { data: isConnected, isLoading: checkingConnection } = useHasConnection()
  const connected = isConnected === true

  const { data: profile } = useMyProfile()
  const { data: transactions = [], isLoading: txLoading, error: txError } = useTransactions(timeRangeDays, connected)
  const { data: categoryInsights = [] } = useCategoryInsights(timeRangeDays, connected)
  const { data: topAccounts = [] } = useTopAccounts(timeRangeDays, connected)
  const { data: topStoresRaw = [] } = useTopStores(timeRangeDays, connected)
  const { data: spendingComparison = null } = useSpendingPeriodComparison(timeRangeDays, connected)
  const { data: spendingSaved = null } = useSpendingSaved(timeRangeDays, connected)
  const initOpenFinance = useInitOpenFinance()

  const insightsError = txError instanceof Error ? txError.message : ""

  const totalSpend = transactions.reduce((sum, tx) => {
    const amount = tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount
    return sum + (typeof amount === "number" ? amount : 0)
  }, 0)

  const periodLabel = timeRangeDays === 365 ? "last year" : `last ${timeRangeDays} days`

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
    <div className="space-y-4 pb-2">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Your money, decoded</h1>
        <p className="text-sm text-muted-foreground">
          {periodLabel.charAt(0).toUpperCase() + periodLabel.slice(1)} · {topAccounts.length} linked accounts
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
            totalSpend={totalSpend}
            periodLabel={periodLabel}
            clubsCount={profile?.clubs?.length ?? 0}
          />
          <StatsGridCard transactionCount={transactions.length} totalAmount={totalSpend} periodLabel={periodLabel} />

          <Carousel setApi={setCarouselApi} opts={{ align: "start" }}>
            <CarouselContent>
              <CarouselItem>
                <SpendingOverviewSlide comparison={spendingComparison} />
              </CarouselItem>
              <CarouselItem>
                <TopCategorySlide categories={categoryInsights} />
              </CarouselItem>
              <CarouselItem>
                <TrueCostSlide transactions={transactions} periodDays={timeRangeDays} />
              </CarouselItem>
              <CarouselItem>
                <TopStoresSlide stores={topStoresRaw} />
              </CarouselItem>
              <CarouselItem>
                <RecentTransactionsSlide transactions={transactions} />
              </CarouselItem>
              <CarouselItem>
                <AccountsSlide accounts={topAccounts} />
              </CarouselItem>
            </CarouselContent>
          </Carousel>
          <CarouselDots api={carouselApi} labels={CAROUSEL_LABELS} />
        </>
      )}
    </div>
  )
}
