import { useAuthStore } from "@/features/auth/store"
import { isTokenExpired, refreshAccessToken } from "@/lib/auth"

const API_GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL ?? "http://localhost:8001"

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
  const obj = value as Record<string, unknown>
  const direct = [obj.message, obj.title, obj.detail, obj.description].flatMap(
    (item) => collectMessages(item),
  )
  const code = collectMessages(obj.code)
  const fieldErrors =
    obj.errors && typeof obj.errors === "object"
      ? Object.entries(obj.errors as Record<string, unknown>).flatMap(
          ([field, fieldValue]) =>
            collectMessages(fieldValue).map((msg) => `${field}: ${msg}`),
        )
      : []
  return Array.from(new Set([...direct, ...code, ...fieldErrors]))
}

function parseApiError(payload: unknown, fallback: string): string {
  const messages = collectMessages(payload)
  return messages.length === 0 ? fallback : messages.join("\n")
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit & { skipAuth?: boolean; errorMessage?: string },
): Promise<T> {
  const { skipAuth, errorMessage, ...fetchOptions } = options ?? {}
  const headers = new Headers(fetchOptions.headers)

  if (!skipAuth) {
    let token = useAuthStore.getState().accessToken
    if (token && isTokenExpired(token)) {
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        useAuthStore.getState().setAccessToken(refreshed)
        token = refreshed
      } else {
        useAuthStore.getState().logout()
        throw new ApiError("Session expired. Please sign in again.", 401)
      }
    }
    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }
  }

  let response: Response
  try {
    response = await fetch(`${API_GATEWAY_URL}${path}`, {
      ...fetchOptions,
      headers,
    })
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError(
        `Cannot reach API Gateway at ${API_GATEWAY_URL}. Check that the service is running.`,
        0,
      )
    }
    throw error
  }

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(
      parseApiError(payload, errorMessage ?? `Request failed (${response.status})`),
      response.status,
    )
  }

  return payload as T
}

export function jsonBody(data: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }
}

export { API_GATEWAY_URL }
