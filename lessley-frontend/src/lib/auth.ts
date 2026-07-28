// Auth is cookie-based: the access and refresh tokens live in Secure/HttpOnly cookies
// the browser sends automatically. JavaScript never sees them. This module only holds
// the CSRF double-submit helper and the cookie-based refresh/logout calls.

const GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL ?? "http://localhost:8001"

export const CSRF_COOKIE = "XSRF-TOKEN"
export const CSRF_HEADER = "X-CSRF-TOKEN"

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"])

/** Reads a readable (non-httpOnly) cookie value, or null. */
export function readCookie(name: string): string | null {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const match = document.cookie.match(new RegExp("(?:^|; )" + escaped + "=([^;]*)"))
  return match ? decodeURIComponent(match[1]) : null
}

/** Adds the X-CSRF-TOKEN header (echoing the XSRF-TOKEN cookie) for state-changing methods. */
export function applyCsrfHeader(headers: Headers, method?: string): Headers {
  if (UNSAFE_METHODS.has((method ?? "GET").toUpperCase())) {
    const token = readCookie(CSRF_COOKIE)
    if (token) headers.set(CSRF_HEADER, token)
  }
  return headers
}

// Singleton promise so several concurrent 401s trigger only one refresh round-trip.
let _refreshPromise: Promise<boolean> | null = null

/** Exchanges the refresh cookie for fresh auth cookies. Returns whether it succeeded. */
export async function refreshAccessToken(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise

  _refreshPromise = (async () => {
    try {
      const headers = new Headers()
      const csrf = readCookie(CSRF_COOKIE)
      if (csrf) headers.set(CSRF_HEADER, csrf)

      const response = await fetch(`${GATEWAY_URL}/api/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers,
      })
      return response.ok
    } catch {
      return false
    } finally {
      _refreshPromise = null
    }
  })()

  return _refreshPromise
}

/** Best-effort server logout: revokes the refresh token and clears the auth cookies. */
export async function logoutRequest(): Promise<void> {
  try {
    const headers = new Headers()
    const csrf = readCookie(CSRF_COOKIE)
    if (csrf) headers.set(CSRF_HEADER, csrf)

    await fetch(`${GATEWAY_URL}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers,
    })
  } catch {
    // State is cleared regardless; the cookies expire on their own if this fails.
  }
}
