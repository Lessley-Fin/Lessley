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

export interface PatchMeRequest {
  clubs?: string[]
  matchLevel?: "Low" | "Medium" | "High" | null
  mutedTags?: string[]
}

interface ConnectionInitResponse {
  connectUrl: string
  connectionId: string
}

export async function fetchMyProfile(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/User/me")
}

export async function patchMyProfile(body: PatchMeRequest): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/User/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

export async function initOpenFinanceConnection(): Promise<ConnectionInitResponse> {
  return apiFetch<ConnectionInitResponse>("/api/User/init", { method: "POST" })
}
