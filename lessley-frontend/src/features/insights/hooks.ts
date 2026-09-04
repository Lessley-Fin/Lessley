import { useEffect } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"

import { useMyProfile, useRecalculateCategories } from "@/features/user/hooks"
import { queryKeys } from "@/lib/query-keys"
import {
  checkHasConnection,
  fetchAccounts,
  fetchCategoryInsights,
  fetchSavingsOpportunities,
  fetchMatchingClubs,
  fetchSpendingByDayInsights,
  fetchSpendingPeriodComparison,
  fetchSpendingSaved,
  fetchSpendingTotal,
  fetchSpendingSavedByAccount,
  fetchTopAccountInsights,
  fetchTopStoreInsights,
  fetchTransactions,
  initOpenFinanceConnection,
} from "./api"

export function useHasConnection() {
  return useQuery({
    queryKey: queryKeys.connection.status(),
    queryFn: checkHasConnection,
    refetchOnWindowFocus: true,
  })
}

/**
 * The user's accounts, fetched once and shared.
 *
 * Insight payloads name an account only by id, so any screen that has to say *where* a
 * purchase came from reads the product and provider off this list.
 */
export function useAccounts(enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.user.accounts(),
    queryFn: fetchAccounts,
    enabled,
  })
}

export function useTransactions(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.transactions.list(days),
    queryFn: () => fetchTransactions(days),
    enabled,
  })
}

export function useCategoryInsights(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.categories(days),
    queryFn: () => fetchCategoryInsights(days),
    enabled,
  })
}

export function useTopAccounts(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.topAccounts(days),
    queryFn: () => fetchTopAccountInsights(days),
    enabled,
  })
}

export function useTopStores(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.topStores(days),
    queryFn: () => fetchTopStoreInsights(days),
    enabled,
  })
}

export function useSpendingByDay(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.spendingByDay(days),
    queryFn: () => fetchSpendingByDayInsights(days),
    enabled,
  })
}

export function useSpendingPeriodComparison(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.spendingPeriodComparison(days),
    queryFn: () => fetchSpendingPeriodComparison(days),
    enabled,
  })
}

export function useSpendingTotal(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.spendingTotal(days),
    queryFn: () => fetchSpendingTotal(days),
    enabled,
  })
}

export function useSpendingSaved(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.spendingSaved(days),
    queryFn: () => fetchSpendingSaved(days),
    enabled,
  })
}

export function useSpendingSavedByAccount(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.spendingSavedByAccount(days),
    queryFn: () => fetchSpendingSavedByAccount(days),
    enabled,
  })
}

export function useMatchingClubs(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.recommendations.list(),
    queryFn: fetchMatchingClubs,
    enabled,
  })
}

export function useInitOpenFinance() {
  return useMutation({
    mutationFn: initOpenFinanceConnection,
  })
}

export function useSavingsOpportunities(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.savingsOpportunities(days),
    queryFn: () => fetchSavingsOpportunities(days),
    enabled,
  })
}

/**
 * Recovers the one state no server-side trigger can reach: a linked bank with no stored tags.
 *
 * Both automatic triggers fire before Open Finance has anything to give. Registration runs
 * before the user has linked a bank at all, and the bank-journey trigger runs as the journey
 * *starts* rather than when consent lands — there is no provider callback to hang it on. So a
 * genuinely new user finishes onboarding with an empty tag list and nothing scheduled to fix it
 * before the weekly sweep. This asks again from the client, which is the only vantage point
 * that exists after the transactions have actually synced.
 *
 * Self-limiting: the request is what makes its own condition false. Once tags are written the
 * Gateway pushes CategoriesUpdated, the profile is refetched, and `tagCount` stops being 0.
 *
 * `tagCount` is a number rather than the array itself on purpose — react-query hands back a
 * fresh array reference on every refetch, so depending on `profile.tags` would re-fire this on
 * each background refresh instead of once per mount.
 */
export function useCategoryBackfill() {
  const { data: isConnected } = useHasConnection()
  const { data: profile } = useMyProfile()
  const { mutate } = useRecalculateCategories()

  const connected = isConnected === true
  const tagCount = profile?.tags.length

  useEffect(() => {
    // Neither loading state can trigger a request: `tagCount` is undefined until the profile
    // lands, and checkHasConnection reports false when the accounts call fails.
    if (!connected || tagCount !== 0) return
    mutate()
  }, [connected, tagCount, mutate])
}
