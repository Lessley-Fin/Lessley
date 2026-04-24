import type { FeedbackSubmission } from "@/lib/types"

export const API_GATEWAY_URL =
  import.meta.env.VITE_API_GATEWAY_URL ?? "http://localhost:5001"
export const PERSONALIZATION_API_URL =
  import.meta.env.VITE_PERSONALIZATION_API_URL ?? "http://localhost:8001"

interface ApiErrorPayload {
  message?: string
  title?: string
}

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
  roles: string[]
}

interface TransactionsResponse {
  items?: Array<{
    id?: string
    accountId?: string
    providerId?: string
  }>
}

function parseApiError(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== "object") return fallback
  const maybeError = payload as ApiErrorPayload
  return maybeError.message ?? maybeError.title ?? fallback
}

function toNetworkError(error: unknown) {
  if (error instanceof TypeError) {
    return new Error(
      `Cannot reach API Gateway at ${API_GATEWAY_URL}. Check that the gateway is running and your URL/CORS are correct.`
    )
  }
  return error
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
    throw toNetworkError(error)
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
    throw toNetworkError(error)
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
    throw toNetworkError(error)
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

export async function submitFeedback(payload: FeedbackSubmission) {
  // Integration-ready stub for the Gateway endpoint once available.
  return Promise.resolve({
    ok: true,
    gatewayUrl: `${API_GATEWAY_URL}/api/feedback`,
    payload,
  })
}
