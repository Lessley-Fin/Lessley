import type {
  FeedbackSubmission,
  PaginatedApiResponse,
  PersonalizationTransaction,
  RecommendationsResponse,
  SpendingCategoryInsight,
  TopAccountInsight,
  TopStoreInsight,
} from "@/lib/types"

export const API_GATEWAY_URL =
  import.meta.env.VITE_API_GATEWAY_URL ?? "http://localhost:8001"

export interface LoginRequest {
  userName: string
  password: string
}

export interface RegisterRequest {
  userName: string
  email: string
  password: string
  clubs?: string[]
  matchLevel?: "Low" | "Medium" | "High"
  mutedCategories?: string[]
}

export interface LoginResponse {
  accessToken: string
  refreshToken: string
}

export interface MeResponse {
  email: string
  userName: string
  roles: string[]
  clubs: string[]
  tags: string[]
  mutedTags: string[]
  matchLevel: "Low" | "Medium" | "High" | null
}

interface ConnectionInitResponse {
  connectUrl: string
  connectionId: string
}

function collectMessages(value: unknown): string[] {
  if (typeof value === "string") {
    return value.trim() ? [value.trim()] : []
  }

  if (Array.isArray(value)) {
    return value.flatMap((item) => collectMessages(item))
  }

  if (!value || typeof value !== "object") {
    return []
  }

  const objectValue = value as Record<string, unknown>
  const directMessages = [
    objectValue.message,
    objectValue.title,
    objectValue.detail,
    objectValue.description,
  ].flatMap((item) => collectMessages(item))

  const code = collectMessages(objectValue.code)
  const fieldErrors = objectValue.errors
  const nestedErrors = fieldErrors && typeof fieldErrors === "object"
    ? Object.entries(fieldErrors as Record<string, unknown>).flatMap(([field, fieldValue]) =>
        collectMessages(fieldValue).map((message) => `${field}: ${message}`)
      )
    : []

  const allMessages = [...directMessages, ...code, ...nestedErrors]
  return Array.from(new Set(allMessages))
}

function parseApiError(payload: unknown, fallback: string) {
  const messages = collectMessages(payload)
  if (messages.length === 0) return fallback
  return messages.join("\n")
}

function toNetworkError(error: unknown) {
  if (error instanceof TypeError) {
    return new Error(
      `Cannot reach API Gateway at ${API_GATEWAY_URL}. Check that the service is running and your URL/CORS are correct.`
    )
  }
  return error
}

async function parseJsonResponse<T>(response: Response, fallbackMessage: string) {
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(parseApiError(payload, fallbackMessage))
  }
  return payload as T
}

function authHeaders(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` }
}

function authJsonHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  }
}

// ── Auth ────────────────────────────────────────────────────────────────────────

export async function loginWithGateway(body: LoginRequest): Promise<LoginResponse> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/Auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(parseApiError(payload, "Unable to sign in with provided credentials."))
    }

    return response.json() as Promise<LoginResponse>
  } catch (error) {
    throw toNetworkError(error)
  }
}

export async function registerWithGateway(body: RegisterRequest) {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/Auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(parseApiError(payload, "Unable to complete registration."))
    }
  } catch (error) {
    throw toNetworkError(error)
  }
}

// ── User Profile ────────────────────────────────────────────────────────────────

export async function getMyProfile(accessToken: string): Promise<MeResponse> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/User/me`, {
      method: "GET",
      headers: authHeaders(accessToken),
    })

    return await parseJsonResponse<MeResponse>(response, "Unable to load user profile.")
  } catch (error) {
    throw toNetworkError(error)
  }
}

// ── Open Finance Connection ─────────────────────────────────────────────────────

export async function initOpenFinanceConnection(accessToken: string): Promise<ConnectionInitResponse> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/User/init`, {
      method: "POST",
      headers: authHeaders(accessToken),
    })

    return await parseJsonResponse<ConnectionInitResponse>(response, "Unable to initiate bank connection.")
  } catch (error) {
    throw toNetworkError(error)
  }
}

export async function checkHasConnection(accessToken: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/User/me/accounts`, {
      headers: authHeaders(accessToken),
    })

    if (!response.ok) return false

    const payload = await response.json().catch(() => null) as PaginatedApiResponse<Record<string, unknown>> | null
    return Array.isArray(payload?.data) && payload.data.length > 0
  } catch {
    return false
  }
}

// ── Transactions ────────────────────────────────────────────────────────────────

export async function getTransactions(
  accessToken: string,
  days: number = 90
): Promise<PersonalizationTransaction[]> {
  try {
    const params = new URLSearchParams({ days: String(days) })
    const response = await fetch(`${API_GATEWAY_URL}/api/User/me/transactions?${params.toString()}`, {
      headers: authHeaders(accessToken),
    })

    const payload = await parseJsonResponse<PaginatedApiResponse<PersonalizationTransaction>>(
      response,
      "Unable to load transactions."
    )
    return Array.isArray(payload.data) ? payload.data : []
  } catch (error) {
    throw toNetworkError(error)
  }
}

// ── Insights ────────────────────────────────────────────────────────────────────

export async function getCategoryInsights(
  accessToken: string,
  days: number = 90
): Promise<SpendingCategoryInsight[]> {
  try {
    const params = new URLSearchParams({ days: String(days) })
    const response = await fetch(`${API_GATEWAY_URL}/api/User/insights/categories?${params.toString()}`, {
      headers: authHeaders(accessToken),
    })

    const payload = await parseJsonResponse<PaginatedApiResponse<SpendingCategoryInsight>>(
      response,
      "Unable to load category insights."
    )
    return Array.isArray(payload.data) ? payload.data : []
  } catch (error) {
    throw toNetworkError(error)
  }
}

export async function getTopAccountInsights(
  accessToken: string,
  days: number = 90
): Promise<TopAccountInsight[]> {
  try {
    const params = new URLSearchParams({ days: String(days) })
    const response = await fetch(`${API_GATEWAY_URL}/api/User/insights/top-accounts?${params.toString()}`, {
      headers: authHeaders(accessToken),
    })

    const payload = await parseJsonResponse<PaginatedApiResponse<TopAccountInsight>>(
      response,
      "Unable to load account insights."
    )
    return Array.isArray(payload.data) ? payload.data : []
  } catch (error) {
    throw toNetworkError(error)
  }
}

export async function getTopStoreInsights(
  accessToken: string,
  days: number = 90
): Promise<TopStoreInsight[]> {
  try {
    const params = new URLSearchParams({ days: String(days) })
    const response = await fetch(`${API_GATEWAY_URL}/api/User/insights/top-stores?${params.toString()}`, {
      headers: authHeaders(accessToken),
    })

    const payload = await parseJsonResponse<PaginatedApiResponse<TopStoreInsight>>(
      response,
      "Unable to load top stores."
    )
    return Array.isArray(payload.data) ? payload.data : []
  } catch (error) {
    throw toNetworkError(error)
  }
}

// ── Recommendations ─────────────────────────────────────────────────────────────

export async function getRecommendations(
  accessToken: string,
): Promise<RecommendationsResponse> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/User/recommendations`, {
      headers: authHeaders(accessToken),
    })

    return await parseJsonResponse<RecommendationsResponse>(
      response,
      "Unable to load recommendations."
    )
  } catch (error) {
    throw toNetworkError(error)
  }
}

export async function triggerMatchingClubs(accessToken: string): Promise<void> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/User/recommendations/matching-clubs`, {
      method: "POST",
      headers: authHeaders(accessToken),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(parseApiError(payload, "Unable to trigger club analysis."))
    }
  } catch (error) {
    throw toNetworkError(error)
  }
}

export async function triggerMissedSavings(accessToken: string): Promise<void> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/User/recommendations/missed-savings`, {
      method: "POST",
      headers: authHeaders(accessToken),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(parseApiError(payload, "Unable to trigger savings analysis."))
    }
  } catch (error) {
    throw toNetworkError(error)
  }
}

// ── Notifications ───────────────────────────────────────────────────────────────

export async function getNotifications(accessToken: string) {
  const response = await fetch(`${API_GATEWAY_URL}/api/Notification`, {
    headers: authHeaders(accessToken),
  })
  if (!response.ok) return []
  return response.json()
}

export async function markAllNotificationsRead(accessToken: string) {
  await fetch(`${API_GATEWAY_URL}/api/Notification/read-all`, {
    method: "POST",
    headers: authHeaders(accessToken),
  })
}

export async function markNotificationRead(notificationId: string, accessToken: string) {
  return fetch(`${API_GATEWAY_URL}/api/Notification/${notificationId}/read`, {
    method: "POST",
    headers: authHeaders(accessToken),
  })
}

// ── User Settings ───────────────────────────────────────────────────────────────

export async function updateUserSettings(
  accessToken: string,
  dto: { mutedTags?: string[]; clubs?: string[]; matchingScore?: number }
) {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/User/me`, {
      method: "PATCH",
      headers: authJsonHeaders(accessToken),
      body: JSON.stringify(dto),
    })

    return await parseJsonResponse(response, "Unable to update settings.")
  } catch (error) {
    throw toNetworkError(error)
  }
}

// ── Feedback (stub) ─────────────────────────────────────────────────────────────

export async function submitFeedback(payload: FeedbackSubmission) {
  return Promise.resolve({
    ok: true,
    gatewayUrl: `${API_GATEWAY_URL}/api/feedback`,
    payload,
  })
}
