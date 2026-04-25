import type {
  FeedbackSubmission,
  PaginatedApiResponse,
  PersonalizationTransaction,
  SpendingCategoryInsight,
  TopAccountInsight,
} from "@/lib/types"

export const API_GATEWAY_URL =
  import.meta.env.VITE_API_GATEWAY_URL ?? "http://localhost:5001"
export const PERSONALIZATION_API_URL =
  import.meta.env.VITE_PERSONALIZATION_API_URL ?? "http://localhost:5002"

export interface LoginRequest {
  userName: string
  password: string
}

export interface RegisterRequest {
  userName: string
  email: string
  password: string
}

export interface LoginResponse {
  accessToken: string
  refreshToken: string
}

export interface MeResponse {
  userId: string
  userName: string
  email?: string
  roles: string[]
}

interface TransactionsResponse {
  items?: Array<{
    id?: string
    accountId?: string
    providerId?: string
  }>
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

function toNetworkError(error: unknown, serviceName: string, serviceUrl: string) {
  if (error instanceof TypeError) {
    return new Error(
      `Cannot reach ${serviceName} at ${serviceUrl}. Check that the service is running and your URL/CORS are correct.`
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

export async function loginWithGateway(body: LoginRequest): Promise<LoginResponse> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/Auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(parseApiError(payload, "Unable to sign in with provided credentials."))
    }

    return response.json() as Promise<LoginResponse>
  } catch (error) {
    throw toNetworkError(error, "API Gateway", API_GATEWAY_URL)
  }
}

export async function registerWithGateway(body: RegisterRequest) {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/Auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(parseApiError(payload, "Unable to complete registration."))
    }
  } catch (error) {
    throw toNetworkError(error, "API Gateway", API_GATEWAY_URL)
  }
}

export async function getMyProfile(accessToken: string): Promise<MeResponse> {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/Auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(parseApiError(payload, "Unable to load user profile."))
    }

    return response.json() as Promise<MeResponse>
  } catch (error) {
    throw toNetworkError(error, "API Gateway", API_GATEWAY_URL)
  }
}

export function getOpenFinanceConnectionUrl(userId: string, returnUrl?: string) {
  const base = `${API_GATEWAY_URL}/api/OpenFinance/connection/${userId}`
  if (!returnUrl) return base
  return `${base}?returnUrl=${encodeURIComponent(returnUrl)}`
}

export async function hasOpenFinanceConnection(userId: string, accessToken?: string) {
  try {
    const response = await fetch(`${API_GATEWAY_URL}/api/OpenFinance/transactions/${userId}`, {
      method: "GET",
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : undefined,
    })

    if (!response.ok) return false

    const payload = (await response.json().catch(() => null)) as TransactionsResponse | null
    const items = payload?.items
    if (!Array.isArray(items) || items.length === 0) return false

    return items.some((item) => Boolean(item?.id || item?.accountId || item?.providerId))
  } catch {
    return false
  }
}

export async function hasPersonalizationConnection(
  userId: string,
  accessToken?: string,
  days: number = 90
) {
  try {
    const params = new URLSearchParams({
      user_id: userId,
      time_filter: "true",
      days: String(days),
    })
    const response = await fetch(`${PERSONALIZATION_API_URL}/open-finance/transactions?${params.toString()}`, {
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : undefined,
    })

    const payload = await parseJsonResponse<PaginatedApiResponse<PersonalizationTransaction>>(
      response,
      "Unable to load transactions."
    )

    return Array.isArray(payload.data) && payload.data.length > 0
  } catch {
    return false
  }
}

export async function getPersonalizationTransactions(
  userId: string,
  accessToken?: string,
  days: number = 90
): Promise<PersonalizationTransaction[]> {
  try {
    const params = new URLSearchParams({
      user_id: userId,
      time_filter: "true",
      days: String(days),
    })
    const response = await fetch(`${PERSONALIZATION_API_URL}/open-finance/transactions?${params.toString()}`, {
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : undefined,
    })

    const payload = await parseJsonResponse<PaginatedApiResponse<PersonalizationTransaction>>(
      response,
      "Unable to load transactions."
    )
    return Array.isArray(payload.data) ? payload.data : []
  } catch (error) {
    throw toNetworkError(error, "Personalization API", PERSONALIZATION_API_URL)
  }
}

export async function getCategoryInsights(
  userId: string,
  accessToken?: string,
  days: number = 90
): Promise<SpendingCategoryInsight[]> {
  try {
    const params = new URLSearchParams({
      user_id: userId,
      time_filter: "true",
      use_mock: "false",
      days: String(days),
    })
    const response = await fetch(`${PERSONALIZATION_API_URL}/insights/categories?${params.toString()}`, {
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : undefined,
    })

    const payload = await parseJsonResponse<PaginatedApiResponse<SpendingCategoryInsight>>(
      response,
      "Unable to load category insights."
    )
    return Array.isArray(payload.data) ? payload.data : []
  } catch (error) {
    throw toNetworkError(error, "Personalization API", PERSONALIZATION_API_URL)
  }
}

export async function getTopAccountInsights(
  userId: string,
  accessToken?: string,
  days: number = 90
): Promise<TopAccountInsight[]> {
  try {
    const params = new URLSearchParams({
      user_id: userId,
      time_filter: "true",
      use_mock: "false",
      days: String(days),
    })
    const response = await fetch(`${PERSONALIZATION_API_URL}/insights/top-accounts?${params.toString()}`, {
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : undefined,
    })

    const payload = await parseJsonResponse<PaginatedApiResponse<TopAccountInsight>>(
      response,
      "Unable to load account insights."
    )
    return Array.isArray(payload.data) ? payload.data : []
  } catch (error) {
    throw toNetworkError(error, "Personalization API", PERSONALIZATION_API_URL)
  }
}

export async function submitFeedback(payload: FeedbackSubmission) {
  // Integration-ready stub for the Gateway endpoint once available.
  return Promise.resolve({
    ok: true,
    gatewayUrl: `${API_GATEWAY_URL}/api/feedback`,
    payload,
  })
}
