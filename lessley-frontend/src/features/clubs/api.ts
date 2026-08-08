import { apiFetch } from "@/lib/api-client"
import type { ClubDto } from "@/lib/types"

export function fetchClubs(): Promise<ClubDto[]> {
  return apiFetch<ClubDto[]>("/api/v1/clubs")
}
