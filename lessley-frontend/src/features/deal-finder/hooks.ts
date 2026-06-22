import { useQuery } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"
import { fetchMccCategories, searchDeals, type DealSearchParams } from "./api"

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
