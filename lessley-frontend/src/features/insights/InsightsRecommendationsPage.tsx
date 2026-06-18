import { useEffect, useState } from "react"
import { ArrowRight, CalendarRange, CheckCircle2, Landmark, Sparkles, Store, TrendingUp } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  getCategoryInsights,
  getClubRecommendations,
  getOpenBankingLookupCandidates,
  getOpenFinanceConnectionUrl,
  getPersonalizationTransactions,
  getTopAccountInsights,
  getTopStoreInsights,
  resolveOpenBankingLookupId,
} from "@/lib/api"
import { fintech } from "@/lib/fintech-styles"
import type {
  ClubRecommendation,
  PersonalizationTransaction,
  SpendingCategoryInsight,
  TopAccountInsight,
  TopStoreInsight,
} from "@/lib/types"

interface InsightsRecommendationsPageProps {
  username: string
  userId: string
  email: string
}

/** Long window so short filters (e.g. 1 week) do not look “disconnected” when older data exists. */
const CONNECTION_PROBE_DAYS = 365

const TIME_RANGE_OPTIONS = [
  { label: "1 week", days: 7 },
  { label: "1 month", days: 30 },
  { label: "90 days", days: 90 },
  { label: "1 year", days: 365 },
] as const

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "ILS",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

function formatAmount(value: number | undefined, currency?: string) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-"
  if (currency && currency !== "ILS") {
    return `${value.toFixed(2)} ${currency}`
  }
  return currencyFormatter.format(value)
}

function formatDate(value: string | undefined) {
  if (!value) return "-"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return "-"
  return parsed.toLocaleDateString()
}

function formatFitPercent(fitScore: number) {
  return `${Math.round(fitScore * 100)}%`
}

function getStoreLabel(store: TopStoreInsight) {
  return store.normalized_merchantName ?? store.merchantName ?? "Unknown store"
}

function getStoreTransactionCount(store: TopStoreInsight) {
  return store.transaction_count ?? store.total_count ?? 0
}

function getStoreTotalAmount(store: TopStoreInsight) {
  return store.transaction_amount ?? store.total_amount ?? 0
}

export function InsightsRecommendationsPage({ username, userId, email }: InsightsRecommendationsPageProps) {
  const [timeRangeDays, setTimeRangeDays] = useState(90)
  const [checkingConnection, setCheckingConnection] = useState(true)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionHint, setConnectionHint] = useState("")
  const [isLoadingPersonalization, setIsLoadingPersonalization] = useState(false)
  const [personalizationError, setPersonalizationError] = useState("")
  const [, setActiveLookupId] = useState("")
  const [transactions, setTransactions] = useState<PersonalizationTransaction[]>([])
  const [categoryInsights, setCategoryInsights] = useState<SpendingCategoryInsight[]>([])
  const [topAccounts, setTopAccounts] = useState<TopAccountInsight[]>([])
  const [topClubRecommendations, setTopClubRecommendations] = useState<ClubRecommendation[]>([])
  const [hasClubAnalysis, setHasClubAnalysis] = useState(false)
  const [topStores, setTopStores] = useState<TopStoreInsight[]>([])

  useEffect(() => {
    let isMounted = true

    const runCheck = async () => {
      const candidates = getOpenBankingLookupCandidates(userId, email, username)
      if (candidates.length === 0) {
        if (isMounted) {
          setIsConnected(false)
          setActiveLookupId("")
          setCheckingConnection(false)
        }
        return
      }

      const accessToken = localStorage.getItem("lessley_access_token") ?? undefined
      const resolvedLookupId = await resolveOpenBankingLookupId(
        candidates,
        accessToken,
        CONNECTION_PROBE_DAYS
      )

      if (isMounted) {
        setIsConnected(Boolean(resolvedLookupId))
        setActiveLookupId(resolvedLookupId)
        setCheckingConnection(false)
        if (resolvedLookupId) {
          setConnectionHint("")
        }
      }
    }

    void runCheck()

    const handleFocus = () => {
      void runCheck()
    }

    window.addEventListener("focus", handleFocus)
    return () => {
      isMounted = false
      window.removeEventListener("focus", handleFocus)
    }
  }, [userId, email, username])

  const handleConnectOpenBanking = () => {
    const openFinanceLookupId = userId || email
    if (!openFinanceLookupId) {
      setConnectionHint("We are still loading your account details. Please try again in a second.")
      return
    }
    const returnUrl = window.location.href
    window.location.assign(getOpenFinanceConnectionUrl(openFinanceLookupId, returnUrl))
  }

  useEffect(() => {
    if (!isConnected) {
      setTransactions([])
      setCategoryInsights([])
      setTopAccounts([])
      setTopClubRecommendations([])
      setHasClubAnalysis(false)
      setTopStores([])
      setPersonalizationError("")
      setIsLoadingPersonalization(false)
      return
    }

    if (!email) return

    let isMounted = true
    const accessToken = localStorage.getItem("lessley_access_token") ?? undefined

    const loadPersonalizationData = async () => {
      setIsLoadingPersonalization(true)
      setPersonalizationError("")
      try {
        const results = await Promise.allSettled([
          getPersonalizationTransactions(email, accessToken, timeRangeDays),
          getCategoryInsights(email, accessToken, timeRangeDays),
          getTopAccountInsights(email, accessToken, timeRangeDays),
          getTopStoreInsights(email, accessToken, timeRangeDays),
          getClubRecommendations(email, accessToken),
        ])
        if (!isMounted) return

        const [txResult, categoriesResult, accountsResult, storesResult, clubResult] = results
        setTransactions(txResult.status === "fulfilled" ? txResult.value : [])
        setCategoryInsights(categoriesResult.status === "fulfilled" ? categoriesResult.value : [])
        setTopAccounts(accountsResult.status === "fulfilled" ? accountsResult.value : [])
        setTopStores(storesResult.status === "fulfilled" ? storesResult.value.slice(0, 3) : [])
        const recommendations =
          clubResult.status === "fulfilled" ? (clubResult.value?.recommendations ?? []) : []
        setHasClubAnalysis(recommendations.length > 0)
        setTopClubRecommendations(recommendations.slice(0, 3))

        const firstError = results.find((r) => r.status === "rejected") as
          | PromiseRejectedResult
          | undefined
        if (firstError) {
          const msg = firstError.reason instanceof Error ? firstError.reason.message : ""
          setPersonalizationError(msg || "Some insights could not be loaded.")
        }
      } catch (error) {
        if (!isMounted) return
        setPersonalizationError(error instanceof Error ? error.message : "Unable to load personalization data.")
      } finally {
        if (isMounted) {
          setIsLoadingPersonalization(false)
        }
      }
    }

    void loadPersonalizationData()

    return () => {
      isMounted = false
    }
  }, [isConnected, email, timeRangeDays])

  const recentTransactions = transactions.slice(0, 5)
  const topCategories = categoryInsights.slice(0, 3)
  const moreHotCategories = categoryInsights.slice(1, 4)
  const accountHighlights = topAccounts.slice(0, 3)
  const topStoreTotalSpend = topStores.reduce((sum, store) => sum + getStoreTotalAmount(store), 0)
  const totalTransactionAmount = transactions.reduce((sum, tx) => {
    const amount = tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount
    return sum + (typeof amount === "number" ? amount : 0)
  }, 0)
  const topCategory = topCategories[0]

  return (
    <section className={fintech.page}>
      {checkingConnection ? (
        <Card className="fintech-card border-0">
          <CardContent className="flex items-center gap-3 py-5">
            <span className="size-4 animate-pulse rounded-full bg-blue-400/50" aria-hidden />
            <p className="text-sm text-slate-500">Verifying bank connection…</p>
          </CardContent>
        </Card>
      ) : isConnected ? (
        <>
          <div className="flex justify-center">
            <span className={fintech.statusConnected}>
              <CheckCircle2 className="size-3.5" />
              Open Banking connected
            </span>
          </div>

          <Card className="fintech-card border-0">
            <CardHeader className="flex-row items-center gap-3 space-y-0 px-5 pb-2 pt-5">
              <div className={fintech.iconWrapBlue}>
                <CalendarRange className="size-4" />
              </div>
              <CardTitle className={fintech.sectionTitle}>Analysis period</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5 pt-0">
              <Label htmlFor="insights-time-range" className="sr-only">
                Time range
              </Label>
              <Select
                value={String(timeRangeDays)}
                onValueChange={(value) => setTimeRangeDays(Number(value))}
              >
                <SelectTrigger id="insights-time-range" className={fintech.select}>
                  <SelectValue placeholder="Choose period" />
                </SelectTrigger>
                <SelectContent className="z-[100]">
                  {TIME_RANGE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.days} value={String(opt.days)}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <Card className="fintech-card border-0">
            <CardHeader className="flex-row items-center gap-3 space-y-0 px-5 pb-2 pt-5">
              <div className={fintech.iconWrapBlue}>
                <TrendingUp className="size-4" />
              </div>
              <CardTitle className={fintech.sectionTitle}>Spending overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 px-5 pb-5 pt-0 text-sm">
              {isLoadingPersonalization ? (
                <p className="text-slate-500">Loading insights…</p>
              ) : null}
              {personalizationError ? (
                <p className="rounded-xl border border-red-200/80 bg-red-50/90 px-3 py-2 text-destructive">
                  {personalizationError}
                </p>
              ) : null}
              {!isLoadingPersonalization && !personalizationError ? (
                <>
                  <div className="grid grid-cols-2 gap-2.5">
                    <div className={fintech.metricBlue}>
                      <p className={fintech.metricLabel}>Transactions</p>
                      <p className={fintech.metricValue}>{transactions.length}</p>
                    </div>
                    <div className={fintech.metricViolet}>
                      <p className={fintech.metricLabel}>Total amount</p>
                      <p className={fintech.metricValue}>{formatAmount(totalTransactionAmount)}</p>
                    </div>
                    <div className={fintech.metricAmber}>
                      <p className={fintech.metricLabel}>Top category</p>
                      <p className="mt-1 line-clamp-1 text-sm font-medium text-slate-800">
                        {topCategory?.category ?? "-"}
                      </p>
                      <p className="text-xs text-slate-500">
                        {topCategory ? `${topCategory.total_count} tx` : "No category data"}
                      </p>
                    </div>
                    <div className={fintech.metricEmerald}>
                      <p className={fintech.metricLabel}>Category spend</p>
                      <p className={fintech.metricValue}>{formatAmount(topCategory?.total_amount)}</p>
                    </div>
                  </div>
                  {moreHotCategories.length ? (
                    <div className="space-y-2">
                      <p className={fintech.sectionEyebrow}>Trending categories</p>
                      {moreHotCategories.map((item) => (
                        <div key={item.category} className={fintech.listRow}>
                          <p className="font-medium text-slate-700">{item.category}</p>
                          <p className={`${fintech.amount} text-sm`}>
                            {item.total_count} tx · {formatAmount(item.total_amount)}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </>
              ) : null}
            </CardContent>
          </Card>

          {!isLoadingPersonalization && !personalizationError ? (
            <Card className="fintech-card border-0">
              <CardHeader className="flex-row items-center gap-3 space-y-0 px-5 pb-2 pt-5">
                <div className={fintech.iconWrapViolet}>
                  <Sparkles className="size-4" />
                </div>
                <div>
                  <CardTitle className={fintech.sectionTitle}>Picked for you</CardTitle>
                  <p className="text-xs text-slate-500">Club fit vs. where you already shop</p>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 px-5 pb-5 pt-0">
                {!hasClubAnalysis ? (
                  <p className="fintech-card-inset text-sm text-slate-600">
                    We need more transaction history to analyze club fit. Try a longer time range or add more
                    purchases through Open Banking.
                  </p>
                ) : (
                  <div className="space-y-2">
                    <p className={fintech.sectionEyebrow}>Top 3 club matches</p>
                    {topClubRecommendations.map((club, index) => (
                      <div key={club.club_id} className={fintech.listRowAccent}>
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
                      </div>
                    ))}
                  </div>
                )}

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <p className={fintech.sectionEyebrow}>Top stores</p>
                    {topStores.length ? (
                      <p className={`${fintech.amount} text-xs`}>{formatAmount(topStoreTotalSpend)} total</p>
                    ) : null}
                  </div>
                  {topStores.length ? (
                    topStores.map((store, index) => (
                      <div key={`${getStoreLabel(store)}-${index}`} className={fintech.listRow}>
                        <span className={fintech.rankBadge}>{index + 1}</span>
                        <div className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-violet-100 text-violet-600">
                          <Store className="size-3.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-slate-800">{getStoreLabel(store)}</p>
                          <p className="text-xs text-slate-500">
                            {getStoreTransactionCount(store)} purchases
                          </p>
                        </div>
                        <p className={`${fintech.amount} shrink-0 text-sm`}>
                          {formatAmount(getStoreTotalAmount(store))}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="fintech-card-inset text-sm text-slate-600">
                      No store patterns yet for this period.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : null}

          <Card className="fintech-card border-0">
            <CardHeader className="px-5 pb-2 pt-5">
              <CardTitle className={fintech.sectionTitle}>Recent transactions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 px-5 pb-5 pt-0 text-sm">
              {isLoadingPersonalization ? <p className="text-slate-500">Loading transactions…</p> : null}
              {!isLoadingPersonalization && recentTransactions.length === 0 ? (
                <p className="text-slate-500">No transactions found.</p>
              ) : null}
              {recentTransactions.map((tx) => {
                const description =
                  tx.merchantName ||
                  tx.description?.description ||
                  tx.description?.fixedText ||
                  tx.description?.initialClean ||
                  "Transaction"
                const amount = tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount
                const currency = tx.amount?.chargedAmount?.currency ?? tx.amount?.originalAmount?.currency ?? ""
                const date =
                  tx.date?.transactionDate || tx.date?.bookingDate || tx.date?.valueDate || tx.createdAt || ""
                return (
                  <div key={tx.id ?? `${description}-${date}`} className={fintech.listRow}>
                    <div className="min-w-0">
                      <p className="font-medium text-slate-800">{description}</p>
                      <p className="text-xs text-slate-500">{formatDate(date)}</p>
                    </div>
                    <p className={`${fintech.amount} shrink-0 text-sm`}>
                      {formatAmount(amount, currency)}
                    </p>
                  </div>
                )
              })}
            </CardContent>
          </Card>

          {accountHighlights.length ? (
            <Card className="fintech-card border-0">
              <CardHeader className="flex-row items-center gap-2 space-y-0 px-5 pb-2 pt-5">
                <Landmark className="size-4 text-slate-500" />
                <CardTitle className={fintech.sectionTitle}>Most active accounts</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 px-5 pb-5 pt-0 text-sm">
                {accountHighlights.map((item) => (
                  <div key={item.accountId} className={fintech.listRow}>
                    <div>
                      <p className="font-medium text-slate-800">{item.accountNumber ?? item.accountId}</p>
                      <p className="text-xs text-slate-500">{item.total_count} transactions</p>
                    </div>
                    <p className={fintech.amount}>{formatAmount(item.total_amount)}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}
        </>
      ) : (
        <Card className="fintech-card overflow-hidden border-0">
          <div className={fintech.gradientBanner}>
            <div className="flex size-10 items-center justify-center rounded-2xl bg-white/20">
              <Landmark className="size-5" />
            </div>
            <CardTitle className="mt-4 text-lg font-semibold text-white">Connect your bank</CardTitle>
            <p className="mt-2 text-sm leading-relaxed text-blue-100">
              Link Open Banking to sync transactions and unlock personalized insights.
            </p>
          </div>
          <CardContent className="space-y-3 px-5 pb-5 pt-4">
            {connectionHint ? <p className="text-xs text-amber-700">{connectionHint}</p> : null}
            <Button className="min-h-12 w-full gap-2" onClick={handleConnectOpenBanking}>
              Connect Open Banking
              <ArrowRight className="size-4" />
            </Button>
            <p className="text-center text-[11px] text-slate-400">
              Regulated Open Banking · Read-only access · You stay in control
            </p>
          </CardContent>
        </Card>
      )}
    </section>
  )
}
