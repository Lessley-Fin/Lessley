import { useEffect, useState } from "react"
import { ArrowRight, CheckCircle2, LogOut } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  getCategoryInsights,
  getOpenFinanceConnectionUrl,
  getPersonalizationTransactions,
  getTopAccountInsights,
  hasPersonalizationConnection,
} from "@/lib/api"
import type {
  PersonalizationTransaction,
  SpendingCategoryInsight,
  TopAccountInsight,
} from "@/lib/types"

interface DashboardPageProps {
  username: string
  userId: string
  email: string
  onLogout: () => void
}

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

export function DashboardPage({
  username,
  userId,
  email,
  onLogout,
}: DashboardPageProps) {
  const [checkingConnection, setCheckingConnection] = useState(true)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionHint, setConnectionHint] = useState("")
  const [isLoadingPersonalization, setIsLoadingPersonalization] = useState(false)
  const [personalizationError, setPersonalizationError] = useState("")
  const [activeLookupId, setActiveLookupId] = useState("")
  const [transactions, setTransactions] = useState<PersonalizationTransaction[]>([])
  const [categoryInsights, setCategoryInsights] = useState<SpendingCategoryInsight[]>([])
  const [topAccounts, setTopAccounts] = useState<TopAccountInsight[]>([])

  useEffect(() => {
    let isMounted = true

    const runCheck = async () => {
      const candidates = Array.from(
        new Set(
          [email, userId, username]
            .map((item) => item.trim())
            .filter(Boolean)
        )
      )
      if (candidates.length === 0) {
        if (isMounted) {
          setIsConnected(false)
          setActiveLookupId("")
          setCheckingConnection(false)
        }
        return
      }

      const accessToken = localStorage.getItem("lessley_access_token") ?? undefined
      let resolvedLookupId = ""
      for (const candidate of candidates) {
        const connected = await hasPersonalizationConnection(candidate, accessToken)
        if (connected) {
          resolvedLookupId = candidate
          break
        }
      }

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
  }, [userId, email])

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
      setPersonalizationError("")
      setIsLoadingPersonalization(false)
      return
    }

    if (!activeLookupId) return

    let isMounted = true
    const accessToken = localStorage.getItem("lessley_access_token") ?? undefined

    const loadPersonalizationData = async () => {
      setIsLoadingPersonalization(true)
      setPersonalizationError("")
      try {
        const [tx, categories, accounts] = await Promise.all([
          getPersonalizationTransactions(activeLookupId, accessToken),
          getCategoryInsights(activeLookupId, accessToken),
          getTopAccountInsights(activeLookupId, accessToken),
        ])
        if (!isMounted) return
        setTransactions(tx)
        setCategoryInsights(categories)
        setTopAccounts(accounts)
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
  }, [isConnected, activeLookupId])

  const recentTransactions = transactions.slice(0, 5)
  const topCategories = categoryInsights.slice(0, 3)
  const moreHotCategories = categoryInsights.slice(1, 4)
  const accountHighlights = topAccounts.slice(0, 3)
  const totalTransactionAmount = transactions.reduce((sum, tx) => {
    const amount = tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount
    return sum + (typeof amount === "number" ? amount : 0)
  }, 0)
  const topCategory = topCategories[0]

  return (
    <main className="mx-auto min-h-svh w-full max-w-md bg-slate-50 pb-28">
      <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between bg-slate-50/95 px-6 pt-3 backdrop-blur">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Lessley</h1>
          <p className="text-sm text-slate-500">Hi {username}</p>
        </div>
        <Button
          className="min-h-11 min-w-11 rounded-xl border-0 bg-white px-3 text-slate-700 shadow-sm hover:bg-slate-100"
          variant="ghost"
          onClick={onLogout}
          aria-label="Logout"
        >
          <LogOut className="size-4" />
          Logout
        </Button>
      </header>

      <section className="space-y-4 px-6 pb-6 pt-4">
        {checkingConnection ? (
          <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
            <CardContent className="pt-5 text-sm text-slate-500">Checking bank connection...</CardContent>
          </Card>
        ) : isConnected ? (
          <>
            <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
              <CardContent className="flex items-center gap-2 pt-5 text-sm text-emerald-700">
                <CheckCircle2 className="size-4" />
                Open Banking connected
              </CardContent>
            </Card>

            <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
              <CardHeader className="pb-2 pt-5">
                <CardTitle className="text-base">Overview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 pt-0 text-sm">
                {isLoadingPersonalization ? <p className="text-slate-500">Loading insights...</p> : null}
                {personalizationError ? <p className="text-destructive">{personalizationError}</p> : null}
                {!isLoadingPersonalization && !personalizationError ? (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl bg-slate-50 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Transactions</p>
                        <p className="mt-1 text-lg font-semibold text-slate-800">{transactions.length}</p>
                      </div>
                      <div className="rounded-xl bg-slate-50 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Total amount</p>
                        <p className="mt-1 text-lg font-semibold text-slate-800">
                          {formatAmount(totalTransactionAmount)}
                        </p>
                      </div>
                      <div className="rounded-xl bg-slate-50 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Top category</p>
                        <p className="mt-1 line-clamp-1 text-sm font-semibold text-slate-800">
                          {topCategory?.category ?? "-"}
                        </p>
                        <p className="text-xs text-slate-500">
                          {topCategory ? `${topCategory.total_count} tx` : "No category data"}
                        </p>
                      </div>
                      <div className="rounded-xl bg-slate-50 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Category spend</p>
                        <p className="mt-1 text-lg font-semibold text-slate-800">
                          {formatAmount(topCategory?.total_amount)}
                        </p>
                      </div>
                    </div>
                    {moreHotCategories.length ? (
                      <div className="space-y-2">
                        <p className="text-xs uppercase tracking-wide text-slate-500">More hot categories</p>
                        {moreHotCategories.map((item) => (
                          <div key={item.category} className="flex items-center justify-between rounded-xl bg-slate-50 p-3">
                            <p className="text-slate-700">{item.category}</p>
                            <p className="text-sm font-medium text-slate-800">
                              {item.total_count} tx - {formatAmount(item.total_amount)}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </>
                ) : null}
              </CardContent>
            </Card>

            <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
              <CardHeader className="pb-2 pt-5">
                <CardTitle className="text-base">Recent transactions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 pt-0 text-sm">
                {isLoadingPersonalization ? <p className="text-slate-500">Loading transactions...</p> : null}
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
                    <div key={tx.id ?? `${description}-${date}`} className="rounded-xl bg-slate-50 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="font-medium text-slate-800">{description}</p>
                          <p className="text-xs text-slate-500">{formatDate(date)}</p>
                        </div>
                        <p className="text-sm font-semibold text-slate-700">{formatAmount(amount, currency)}</p>
                      </div>
                    </div>
                  )
                })}
              </CardContent>
            </Card>

            {accountHighlights.length ? (
              <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
                <CardHeader className="pb-2 pt-5">
                  <CardTitle className="text-base">Most active accounts</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 pt-0 text-sm">
                  {accountHighlights.map((item) => (
                    <div key={item.accountId} className="flex items-center justify-between rounded-xl bg-slate-50 p-3">
                      <div>
                        <p className="font-medium text-slate-800">{item.accountNumber ?? item.accountId}</p>
                        <p className="text-xs text-slate-500">{item.total_count} transactions</p>
                      </div>
                      <p className="font-semibold text-slate-700">{formatAmount(item.total_amount)}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : null}
          </>
        ) : (
          <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
            <CardHeader className="pb-2 pt-5">
              <CardTitle className="text-base">Connect your bank</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              <p className="text-sm text-slate-500">
                You are not connected to Open Banking yet. Connect now to sync transactions.
              </p>
              {connectionHint ? <p className="text-xs text-slate-500">{connectionHint}</p> : null}
              <Button className="min-h-11 rounded-xl" onClick={handleConnectOpenBanking}>
                Connect Open Banking
                <ArrowRight className="size-4" />
              </Button>
            </CardContent>
          </Card>
        )}
      </section>
    </main>
  )
}
