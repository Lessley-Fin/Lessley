import { useQuery } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"
import { fetchDealById, fetchMccCategories, searchDeals, type DealSearchParams } from "./api"

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

export function useDealById(dealId: string | null) {
  return useQuery({
    queryKey: queryKeys.dealFinder.byId(dealId ?? ""),
    queryFn: () => fetchDealById(dealId!),
    enabled: !!dealId,
    staleTime: 5 * 60 * 1000,
  })
}
