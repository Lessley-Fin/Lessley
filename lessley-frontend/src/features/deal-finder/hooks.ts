import { useQuery } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"
import {
  fetchDealById,
  fetchHotDeals,
  fetchMccCategories,
  searchDeals,
  type DealSearchParams,
} from "./api"

export function useMccCategories() {
  return useQuery({
    queryKey: queryKeys.dealFinder.categories(),
    queryFn: fetchMccCategories,
    staleTime: 5 * 60 * 1000,
  })
}

export function useDealSearch(params: DealSearchParams, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.dealFinder.search(params),
    queryFn: () => searchDeals(params),
    enabled,
  })
}

/**
 * The interest-ranked feed. Kept fresh for a couple of minutes: the underlying score only
 * moves once a night, and the exploration slice is re-drawn on every request — refetching on
 * every focus would reshuffle the list under a user who just looked away.
 */
export function useHotDeals(limit = 10) {
  return useQuery({
    queryKey: queryKeys.dealFinder.hot(limit),
    queryFn: () => fetchHotDeals(limit),
    staleTime: 2 * 60 * 1000,
  })
}

export function useDealById(dealId: string | null) {
  return useQuery({
    queryKey: queryKeys.dealFinder.byId(dealId ?? ""),
    queryFn: () => fetchDealById(dealId!),
    enabled: !!dealId,
    staleTime: 5 * 60 * 1000,
  })
}
