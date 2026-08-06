import { useQuery } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"
import { fetchClubs } from "./api"

export function useClubs() {
  return useQuery({
    queryKey: queryKeys.clubs.all(),
    queryFn: fetchClubs,
    staleTime: 5 * 60 * 1000,
  })
}
