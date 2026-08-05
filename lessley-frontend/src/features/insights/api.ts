import { apiFetch } from "@/lib/api-client"
import type {
  PaginatedApiResponse,
  PersonalizationTransaction,
  RecommendationsResponse,
  SpendingCategoryInsight,
  TopAccountInsight,
  TopStoreInsight,
} from "@/lib/types"

interface ConnectionInitResponse {
  connectUrl: string
  connectionId: string
}

export async function checkHasConnection(): Promise<boolean> {
  try {
    const payload = await apiFetch<PaginatedApiResponse<Record<string, unknown>> | null>(
      "/api/v1/open-finance/accounts",
    )
    return Array.isArray(payload?.data) && payload.data.length > 0
  } catch {
    return false
  }
}

export async function initOpenFinanceConnection(): Promise<ConnectionInitResponse> {
  return apiFetch<ConnectionInitResponse>("/api/v1/User/init", { method: "POST" })
}

export async function fetchTransactions(
  days: number = 90,
): Promise<PersonalizationTransaction[]> {
  const params = new URLSearchParams({ days: String(days) })
  const payload = await apiFetch<PaginatedApiResponse<PersonalizationTransaction>>(
    `/api/v1/open-finance/transactions?${params.toString()}`,
  )
  return Array.isArray(payload.data) ? payload.data : []
}

export async function fetchCategoryInsights(
  days: number = 90,
): Promise<SpendingCategoryInsight[]> {
  const params = new URLSearchParams({ days: String(days) })
  const payload = await apiFetch<PaginatedApiResponse<SpendingCategoryInsight>>(
    `/api/v1/insights/categories?${params.toString()}`,
  )
  return Array.isArray(payload.data) ? payload.data : []
}

export async function fetchTopAccountInsights(
  days: number = 90,
): Promise<TopAccountInsight[]> {
  const params = new URLSearchParams({ days: String(days) })
  const payload = await apiFetch<PaginatedApiResponse<TopAccountInsight>>(
    `/api/v1/insights/top-accounts?${params.toString()}`,
  )
  return Array.isArray(payload.data) ? payload.data : []
}

export async function fetchTopStoreInsights(
  days: number = 90,
): Promise<TopStoreInsight[]> {
  const params = new URLSearchParams({ days: String(days) })
  const payload = await apiFetch<PaginatedApiResponse<TopStoreInsight>>(
    `/api/v1/insights/top-stores?${params.toString()}`,
  )
  return Array.isArray(payload.data) ? payload.data : []
}

export async function fetchRecommendations(): Promise<RecommendationsResponse> {
  return apiFetch<RecommendationsResponse>("/api/v1/User/recommendations")
}

export async function triggerMatchingClubs(): Promise<void> {
  await apiFetch("/api/v1/User/recommendations/matching-clubs", {
    method: "POST",
  })
}

export async function triggerMissedSavings(): Promise<void> {
  await apiFetch("/api/v1/User/recommendations/missed-savings", {
    method: "POST",
  })
}
