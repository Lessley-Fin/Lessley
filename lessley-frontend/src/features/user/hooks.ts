import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
import { queryKeys } from "@/lib/query-keys"
import { deleteMyAccount, fetchMyProfile, initOpenFinanceConnection, patchMyProfile } from "./api"

export function useMyProfile() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return useQuery({
    queryKey: queryKeys.user.profile(),
    queryFn: fetchMyProfile,
    enabled: isAuthenticated,
  })
}

export function useUpdateMyProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: patchMyProfile,
    // The PATCH response is a narrower shape than the full profile (e.g. no `roles`), so
    // refetch instead of caching it directly — setQueryData here previously clobbered
    // `roles` with undefined and crashed MainShell's `profile.roles.includes(...)`.
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.user.profile() })

      // A club, match-level or muted-tag change invalidates what is on screen. Club matching
      // is a plain query now, so dropping the cache is the whole job — the next render asks
      // again. A match-level change also queues a category recalculation server-side, which
      // arrives later as a CategoriesUpdated push.
      if (data.staleInsights) {
        queryClient.invalidateQueries({ queryKey: queryKeys.recommendations.list() })
      }
    },
  })
}

export function useInitOpenFinance() {
  return useMutation({
    mutationFn: initOpenFinanceConnection,
  })
}

export function useDeleteMyAccount() {
  return useMutation({
    mutationFn: deleteMyAccount,
  })
}
