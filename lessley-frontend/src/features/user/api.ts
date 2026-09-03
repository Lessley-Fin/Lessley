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

export interface DeleteAccountRequest {
  /** The caller's own username or email — confirmation, not identity: the server uses the session. */
  userNameOrEmail: string
  password: string
  /** Also revoke the Open Finance bank consent, not just the Lessley account. */
  closeOpenFinanceConnection: boolean
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
 * Permanently deletes the signed-in account. Answers 204 with the auth cookies cleared.
 *
 * Failures are told apart by status, not by message: 400 is bad credentials (deliberately
 * never 401, which apiFetch would read as an expired session and sign the user out), 423 is
 * the lockout, and 502 means the bank connection could not be closed and *nothing* was deleted.
 */
export async function deleteMyAccount(body: DeleteAccountRequest): Promise<void> {
  return apiFetch<void>("/api/v1/User/me", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}
