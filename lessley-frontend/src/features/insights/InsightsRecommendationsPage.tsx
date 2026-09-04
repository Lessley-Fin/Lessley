import { useState } from "react"
import { useTranslation } from "react-i18next"

import { CarouselDots } from "@/components/shared/CarouselDots"
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel"
import { useMyProfile } from "@/features/user/hooks"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { getDirection } from "@/lib/i18n/config"
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
import { TransactionMixSlide } from "./components/TransactionMixSlide"
import {
  useCategoryBackfill,
  useCategoryInsights,
  useHasConnection,
  useInitOpenFinance,
  useSpendingPeriodComparison,
  useSpendingSaved,
  useSpendingTotal,
  useTopAccounts,
  useTopStores,
  useTransactions,
} from "./hooks"

export function InsightsRecommendationsPage() {
  const { t, i18n } = useTranslation()
  const direction = getDirection(i18n.language)
  const CAROUSEL_LABELS = [
    t("insights.carousel.overview"),
    t("insights.carousel.categories"),
    t("insights.carousel.topStores"),
    t("insights.carousel.transactions"),
    t("insights.carousel.accounts"),
    t("insights.carousel.mix"),
  ]

  function periodLabelFor(days: number) {
    return days === 365 ? t("insights.period.lastYear") : t("insights.period.lastDays", { count: days })
  }

  const [timeRangeDays, setTimeRangeDays] = useState<number>(INSIGHTS_DEFAULTS.DEFAULT_TIME_RANGE_DAYS)
  const [deepDiveDays, setDeepDiveDays] = useState<number>(INSIGHTS_DEFAULTS.DEFAULT_TIME_RANGE_DAYS)
  const [carouselApi, setCarouselApi] = useState<CarouselApi>()

  const { data: isConnected, isLoading: checkingConnection } = useHasConnection()
  const connected = isConnected === true

  const { data: profile } = useMyProfile()

  // Onboarding can leave a new user with a linked bank and no categories; ask again from here.
  useCategoryBackfill()

  // Not summed on the client. Falling back to originalAmount when the charge is blank counted
  // voucher purchases as money spent, and the rules for what a row is worth live in one place
  // on the backend — see TransactionAmountService. This also replaces a full-year transaction
  // fetch that existed only to drive the spinner below.
  const {
    data: spendingTotal = null,
    isLoading: txLoading,
    error: txError,
  } = useSpendingTotal(timeRangeDays, connected)
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
  // The mix slide follows the deep-dive range, which moves independently of the range above.
  const { data: deepDiveTotal = null } = useSpendingTotal(deepDiveDays, connected)

  const initOpenFinance = useInitOpenFinance()

  const insightsError = txError instanceof Error ? txError.message : ""
  const deepDiveErrorMessage = deepDiveError instanceof Error ? deepDiveError.message : ""

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
        <h1 className="text-2xl font-bold tracking-tight">{t("insights.page.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {periodLabel.charAt(0).toUpperCase() + periodLabel.slice(1)} ·{" "}
          {t("insights.page.linkedAccounts", { count: linkedAccounts.length })}
        </p>
      </div>

      <AnalysisPeriodCard value={timeRangeDays} onChange={setTimeRangeDays} />

      {txLoading ? (
        <p className="text-sm text-muted-foreground">{t("insights.page.loadingInsights")}</p>
      ) : insightsError ? (
        <p className="text-sm text-destructive">{insightsError}</p>
      ) : (
        <>
          <SavingsHeroCard
            totalSaved={spendingSaved?.total_amount ?? 0}
            breakdown={spendingSaved?.breakdown ?? []}
            periodLabel={periodLabel}
            clubsCount={profile?.clubs?.length ?? 0}
          />
          <StatsGridCard
            transactionCount={spendingTotal?.purchase_count ?? 0}
            totalAmount={spendingTotal?.total_amount ?? 0}
            periodLabel={periodLabel}
            composition={spendingTotal?.mix}
          />
        </>
      )}

      <div className="space-y-3 border-t border-border/70 pt-5">
        <div>
          <h2 className="text-lg font-bold tracking-tight">{t("insights.page.deepDiveTitle")}</h2>
          <p className="text-sm text-muted-foreground">
            {t("insights.page.deepDiveSubtitle", { period: deepDivePeriodLabel })}
          </p>
        </div>

        <AnalysisPeriodCard value={deepDiveDays} onChange={setDeepDiveDays} />

        {deepDiveLoading ? (
          <p className="text-sm text-muted-foreground">{t("insights.page.loadingInsights")}</p>
        ) : deepDiveErrorMessage ? (
          <p className="text-sm text-destructive">{deepDiveErrorMessage}</p>
        ) : (
          <>
            <Carousel setApi={setCarouselApi} opts={{ align: "start", direction }}>
              <CarouselContent>
                <CarouselItem>
                  <SpendingOverviewSlide comparison={spendingComparison} days={deepDiveDays} />
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
                <CarouselItem>
                  <TransactionMixSlide
                    composition={deepDiveTotal?.mix ?? []}
                    periodLabel={deepDivePeriodLabel}
                    totalAmount={deepDiveTotal?.total_amount ?? 0}
                  />
                </CarouselItem>
              </CarouselContent>
              <div className="mt-4 flex items-center justify-center gap-3">
                <CarouselPrevious aria-label={t("common.previousSlide")} />
                <CarouselDots api={carouselApi} labels={CAROUSEL_LABELS} />
                <CarouselNext aria-label={t("common.nextSlide")} />
              </div>
            </Carousel>
          </>
        )}
      </div>
    </div>
  )
}
