const GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL ?? "http://localhost:8001"

export const SESSION_KEYS = {
  session: "lessley_poc_session",
  accessToken: "lessley_access_token",
  refreshToken: "lessley_refresh_token",
  username: "lessley_username",
  userId: "lessley_user_id",
  email: "lessley_user_email",
} as const

export interface SessionData {
  accessToken: string
  refreshToken: string
  username?: string
  userId?: string
  email?: string
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const part = token.split(".")[1]
    if (!part) return null
    const normalized = part.replace(/-/g, "+").replace(/_/g, "/")
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4)
    return JSON.parse(atob(padded)) as Record<string, unknown>
  } catch {
    return null
  }
}

export function getEmailFromToken(token: string): string {
  const payload = decodeJwtPayload(token)
  if (!payload) return ""
  const candidates = [
    payload.email,
    payload.upn,
    payload.preferred_username,
    payload["http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"],
  ]
  const match = candidates.find((c) => typeof c === "string" && c.includes("@"))
  return typeof match === "string" ? match.trim().toLowerCase() : ""
}

// Returns true if the JWT has expired (or will expire within bufferSeconds).
export function isTokenExpired(token: string, bufferSeconds = 60): boolean {
  const payload = decodeJwtPayload(token)
  if (!payload) return true
  const exp = payload.exp
  if (typeof exp !== "number") return true
  return Date.now() / 1000 > exp - bufferSeconds
}

export function isAuthenticated(): boolean {
  return localStorage.getItem(SESSION_KEYS.session) === "active"
}

export function getAccessToken(): string | null {
  return localStorage.getItem(SESSION_KEYS.accessToken)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(SESSION_KEYS.refreshToken)
}

export function storeSession(data: SessionData): void {
  localStorage.setItem(SESSION_KEYS.session, "active")
  localStorage.setItem(SESSION_KEYS.accessToken, data.accessToken)
  localStorage.setItem(SESSION_KEYS.refreshToken, data.refreshToken)
  if (data.username) localStorage.setItem(SESSION_KEYS.username, data.username)
  if (data.userId) localStorage.setItem(SESSION_KEYS.userId, data.userId)
  if (data.email) localStorage.setItem(SESSION_KEYS.email, data.email)
}

export function clearSession(): void {
  Object.values(SESSION_KEYS).forEach((key) => localStorage.removeItem(key))
}

// Singleton promise — deduplicates concurrent refresh calls so only one
// in-flight request runs at a time even if multiple API calls trigger refresh.
let _refreshPromise: Promise<string | null> | null = null

export async function refreshAccessToken(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise

  _refreshPromise = (async () => {
    try {
      const token = getRefreshToken()
      if (!token) return null

      const response = await fetch(`${GATEWAY_URL}/api/Auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken: token }),
      })

      if (!response.ok) {
        clearSession()
        return null
      }

      const data = (await response.json()) as { accessToken: string; refreshToken?: string }
      localStorage.setItem(SESSION_KEYS.accessToken, data.accessToken)
      if (data.refreshToken) {
        localStorage.setItem(SESSION_KEYS.refreshToken, data.refreshToken)
      }
      return data.accessToken
    } catch {
      return null
    } finally {
      _refreshPromise = null
    }
  })()

  return _refreshPromise
}

// Returns a valid (non-expired) access token, automatically refreshing if needed.
export async function getValidAccessToken(): Promise<string | null> {
  const token = getAccessToken()
  if (!token) return null
  if (!isTokenExpired(token)) return token
  return refreshAccessToken()
}
