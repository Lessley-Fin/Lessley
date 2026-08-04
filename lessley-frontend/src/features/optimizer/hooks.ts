import { useQuery } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"
import { optimizeCart, searchStores, type OptimizeParams } from "./api"

export function useStoreSearch(storeText: string) {
  const trimmed = storeText.trim()
  return useQuery({
    queryKey: queryKeys.optimizer.stores(trimmed),
    queryFn: () => searchStores(trimmed),
    // Two characters is the shortest fragment worth a round-trip; below that
    // the deal search matches too broadly to be a useful store picker.
    enabled: trimmed.length >= 2,
    staleTime: 5 * 60 * 1000,
  })
}

export function useOptimizeCart(params: OptimizeParams | null) {
  return useQuery({
    queryKey: queryKeys.optimizer.optimize(params ?? {}),
    queryFn: () => optimizeCart(params!),
    enabled: params !== null,
  })
}
