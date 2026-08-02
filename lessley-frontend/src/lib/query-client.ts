import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
import { ApiError } from "./api-client"

function handleGlobalError(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    useAuthStore.getState().logout()
  }
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: handleGlobalError }),
  mutationCache: new MutationCache({ onError: handleGlobalError }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60 * 1000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status === 401) return false
        return failureCount < 1
      },
      refetchOnWindowFocus: true,
    },
  },
})
