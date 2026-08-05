import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
import { triggerMatchingClubs, triggerMissedSavings } from "@/features/insights/api"
import { queryKeys } from "@/lib/query-keys"
import { fetchMyProfile, initOpenFinanceConnection, patchMyProfile } from "./api"

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

      // Club/match-level/muted-tag changes invalidate cached recommendations, but nothing
      // recalculates them eagerly anymore — Personalization does it, and only if asked.
      // Best-effort: the user has no categories yet (never connected a bank), an unrelated
      // failure here shouldn't block the settings save that already succeeded.
      if (data.staleInsights) {
        void triggerMatchingClubs().catch(() => {})
        void triggerMissedSavings().catch(() => {})
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
