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

// Narrower than MeResponse (no `roles`) and adds a flag GET /me doesn't have — the two
// endpoints intentionally return different shapes, so don't merge this into MeResponse.
export interface PatchMeResponse {
  email: string
  userName: string
  clubs: string[]
  tags: string[]
  mutedTags: string[]
  matchLevel: "Low" | "Medium" | "High" | null
  // True when the club/match-level/muted-tag change invalidates cached
  // recommendations — Personalization needs to be asked to recalculate them.
  staleInsights: boolean
}

interface ConnectionInitResponse {
  connectUrl: string
  connectionId: string
}

export async function fetchMyProfile(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/v1/User/me")
}

export async function patchMyProfile(body: PatchMeRequest): Promise<PatchMeResponse> {
  return apiFetch<PatchMeResponse>("/api/v1/User/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

export async function initOpenFinanceConnection(): Promise<ConnectionInitResponse> {
  return apiFetch<ConnectionInitResponse>("/api/v1/User/init", { method: "POST" })
}

/**
 * Permanently deletes the signed-in account, along with its bank connection. Answers 204 with
 * the auth cookies cleared.
 *
 * Sends no body on purpose: the account deleted is the one in the session, and the confirmation
 * the user types is checked here in the client. A 502 means the bank connection could not be
 * closed and *nothing* was deleted.
 */
export async function deleteMyAccount(): Promise<void> {
  return apiFetch<void>("/api/v1/User/me", { method: "DELETE" })
}

/**
 * Asks the Gateway to recalculate this user's spending categories.
 *
 * Nothing useful comes back: the Gateway publishes a command and answers 202 while the
 * calculation is still travelling the bus. The tags arrive later as a CategoriesUpdated push.
 */
export async function requestCategoryRecalculation(): Promise<void> {
  await apiFetch<void>("/api/v1/User/recalculate-categories", { method: "POST" })
}
