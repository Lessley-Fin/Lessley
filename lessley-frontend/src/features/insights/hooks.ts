import { useMutation, useQuery } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"
import {
  checkHasConnection,
  fetchCategoryInsights,
  fetchMissedSavingsByStore,
  fetchRecommendations,
  fetchSpendingByDayInsights,
  fetchSpendingPeriodComparison,
  fetchSpendingSaved,
  fetchSpendingSavedByAccount,
  fetchTopAccountInsights,
  fetchTopStoreInsights,
  fetchTransactions,
  initOpenFinanceConnection,
  triggerMatchingClubs,
  triggerMissedSavings,
} from "./api"

export function useHasConnection() {
  return useQuery({
    queryKey: queryKeys.connection.status(),
    queryFn: checkHasConnection,
    refetchOnWindowFocus: true,
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

export function useRecommendations(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.recommendations.list(),
    queryFn: fetchRecommendations,
    enabled,
  })
}

export function useInitOpenFinance() {
  return useMutation({
    mutationFn: initOpenFinanceConnection,
  })
}

export function useTriggerMatchingClubs() {
  return useMutation({
    mutationFn: triggerMatchingClubs,
  })
}

export function useTriggerMissedSavings() {
  return useMutation({
    mutationFn: triggerMissedSavings,
  })
}

export function useMissedSavingsByStore(days: number, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.insights.missedSavingsByStore(days),
    queryFn: () => fetchMissedSavingsByStore(days),
    enabled,
  })
}
