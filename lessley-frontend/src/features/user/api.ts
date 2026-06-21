import { apiFetch } from "@/lib/api-client"

export interface MeResponse {
  email: string
  userName: string
  roles: string[]
  clubs: string[]
  tags: string[]
  mutedTags: string[]
  matchLevel: "Low" | "Medium" | "High" | null
}

export async function fetchMyProfile(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/User/me")
}
