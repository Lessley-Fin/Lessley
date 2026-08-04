import { useState } from "react"
import { CheckCircle2 } from "lucide-react"

import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { ActiveAccountsCard } from "./components/ActiveAccountsCard"
import { AnalysisPeriodCard } from "./components/AnalysisPeriodCard"
import { ConnectBankCard } from "./components/ConnectBankCard"
import { ConnectionCheck } from "./components/ConnectionCheck"
import { RecentTransactionsCard } from "./components/RecentTransactionsCard"
import { SpendingOverviewCard } from "./components/SpendingOverviewCard"
import { TopStoresCard } from "./components/TopStoresCard"
import {
  useCategoryInsights,
  useHasConnection,
  useInitOpenFinance,
  useTopAccounts,
  useTopStores,
  useTransactions,
} from "./hooks"

export function InsightsRecommendationsPage() {
  const [timeRangeDays, setTimeRangeDays] = useState<number>(INSIGHTS_DEFAULTS.DEFAULT_TIME_RANGE_DAYS)

  const { data: isConnected, isLoading: checkingConnection } = useHasConnection()
  const connected = isConnected === true

  const { data: transactions = [], isLoading: txLoading, error: txError } = useTransactions(timeRangeDays, connected)
  const { data: categoryInsights = [] } = useCategoryInsights(timeRangeDays, connected)
  const { data: topAccounts = [] } = useTopAccounts(timeRangeDays, connected)
  const { data: topStoresRaw = [] } = useTopStores(timeRangeDays, connected)
  const initOpenFinance = useInitOpenFinance()

  const accountHighlights = topAccounts.slice(0, INSIGHTS_DEFAULTS.ACCOUNT_HIGHLIGHTS_LIMIT)
  const insightsError = txError instanceof Error ? txError.message : ""

  const handleConnectOpenBanking = () => {
    initOpenFinance.mutate(undefined, {
      onSuccess: (data) => {
        window.location.assign(data.connectUrl)
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
        <ConnectBankCard
          onConnect={handleConnectOpenBanking}
          isPending={initOpenFinance.isPending}
          error={initOpenFinance.error}
        />
      </section>
    )
  }

  return (
    <section className={fintech.page}>
      <div className="flex justify-center">
        <span className={fintech.statusConnected}>
          <CheckCircle2 className="size-3.5" />
          Open Banking connected
        </span>
      </div>

      <AnalysisPeriodCard value={timeRangeDays} onChange={setTimeRangeDays} />
      <SpendingOverviewCard
        transactions={transactions}
        categories={categoryInsights}
        isLoading={txLoading}
        error={insightsError}
      />

      {!txLoading && !insightsError ? (
        <TopStoresCard stores={topStoresRaw} />
      ) : null}

      <RecentTransactionsCard transactions={transactions} isLoading={txLoading} />
      <ActiveAccountsCard accounts={accountHighlights} />
    </section>
  )
}
