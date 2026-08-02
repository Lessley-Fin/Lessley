import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
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
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.user.profile(), data)
    },
  })
}

export function useInitOpenFinance() {
  return useMutation({
    mutationFn: initOpenFinanceConnection,
  })
}
