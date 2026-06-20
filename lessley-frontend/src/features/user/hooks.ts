import { useQuery } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
import { queryKeys } from "@/lib/query-keys"
import { fetchMyProfile } from "./api"

export function useMyProfile() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return useQuery({
    queryKey: queryKeys.user.profile(),
    queryFn: fetchMyProfile,
    enabled: isAuthenticated,
  })
}
