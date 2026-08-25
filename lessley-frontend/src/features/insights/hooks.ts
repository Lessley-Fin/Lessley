import { useMutation, useQuery } from "@tanstack/react-query"

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
