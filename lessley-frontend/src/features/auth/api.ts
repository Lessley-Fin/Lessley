import { apiFetch, jsonBody } from "@/lib/api-client"

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
  return apiFetch<AuthProfileResponse>("/api/auth/login", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to sign in with provided credentials.",
  })
}

export async function registerWithGateway(body: RegisterRequest): Promise<void> {
  await apiFetch<void>("/api/auth/register", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to complete registration.",
  })
}
