import { useQuery } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"
import { searchDeals, type DealSearchParams } from "./api"

export function useDealSearch(params: DealSearchParams, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.dealFinder.search(params),
    queryFn: () => searchDeals(params),
    enabled,
  })
}
