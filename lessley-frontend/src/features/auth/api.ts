import { apiFetch, jsonBody } from "@/lib/api-client"

export interface LoginRequest {
  userName: string
  password: string
}

// Tokens now arrive as httpOnly cookies; the body carries only non-sensitive profile info.
export interface AuthProfileResponse {
  userName: string
  email: string
  userId: string
  roles: string[]
}

export async function loginWithGateway(
  body: LoginRequest,
): Promise<AuthProfileResponse> {
  return apiFetch<AuthProfileResponse>("/api/v1/auth/login", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to sign in with provided credentials.",
  })
}

/**
 * Code rules, reported by every endpoint that sends a code so the client never keeps its own
 * copy of the server's timings. Note that the two durations are unrelated: `codeTtlMinutes` is
 * how long the code works, `resendCooldownSeconds` only gates asking for a replacement.
 */
export interface VerificationPolicy {
  codeLength: number
  codeTtlMinutes: number
  resendCooldownSeconds: number
}

// ── Registration ────────────────────────────────────────────────────────────
// Three calls, and only the last one creates an account. The registrationToken returned by
// `start` identifies the in-flight signup; it is worthless on its own until the emailed code
// has been verified, and it expires if the wizard is abandoned.

export interface StartRegistrationRequest {
  userName: string
  email: string
  password: string
}

export interface StartRegistrationResponse {
  registrationToken: string
  email: string
  codeExpiresAt: string
  expiresAt: string
  policy: VerificationPolicy
}

export async function startRegistration(
  body: StartRegistrationRequest,
): Promise<StartRegistrationResponse> {
  return apiFetch<StartRegistrationResponse>("/api/v1/auth/register/start", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to start registration.",
  })
}

export async function verifyRegistrationEmail(body: {
  registrationToken: string
  code: string
}): Promise<{ verified: boolean; email: string }> {
  return apiFetch("/api/v1/auth/register/verify-email", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to verify that code.",
  })
}

export async function resendRegistrationCode(body: {
  registrationToken: string
}): Promise<{ codeExpiresAt: string; policy: VerificationPolicy }> {
  return apiFetch("/api/v1/auth/register/resend-code", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to send another code.",
  })
}

export interface CompleteRegistrationRequest {
  registrationToken: string
  clubs?: string[]
  matchLevel?: "Low" | "Medium" | "High"
  mutedCategories?: string[]
}

/** Creates the account and signs the user in, returning the same profile shape as login. */
export async function completeRegistration(
  body: CompleteRegistrationRequest,
): Promise<AuthProfileResponse> {
  return apiFetch<AuthProfileResponse>("/api/v1/auth/register/complete", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to complete registration.",
  })
}

// ── Password reset ──────────────────────────────────────────────────────────

export async function requestPasswordReset(body: {
  email: string
}): Promise<{ message: string; policy: VerificationPolicy }> {
  return apiFetch("/api/v1/auth/password/forgot", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to send a reset code.",
  })
}

export async function verifyPasswordResetCode(body: {
  email: string
  code: string
}): Promise<{ resetTicket: string; expiresAt: string }> {
  return apiFetch("/api/v1/auth/password/verify-code", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to verify that code.",
  })
}

export async function resetPassword(body: {
  email: string
  resetTicket: string
  newPassword: string
}): Promise<{ message: string }> {
  return apiFetch("/api/v1/auth/password/reset", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to change your password.",
  })
}

// ── Passwordless sign-in ────────────────────────────────────────────────────

export async function requestLoginCode(body: {
  email: string
}): Promise<{ message: string; policy: VerificationPolicy }> {
  return apiFetch("/api/v1/auth/login/otp/request", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to send a sign-in code.",
  })
}

export async function verifyLoginCode(body: {
  email: string
  code: string
}): Promise<AuthProfileResponse> {
  return apiFetch<AuthProfileResponse>("/api/v1/auth/login/otp/verify", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to sign in with that code.",
  })
}
