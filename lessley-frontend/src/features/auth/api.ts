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

export interface LoginResponse {
  accessToken: string
  refreshToken: string
}

export async function loginWithGateway(
  body: LoginRequest,
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/api/Auth/login", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to sign in with provided credentials.",
  })
}

export async function registerWithGateway(body: RegisterRequest): Promise<void> {
  await apiFetch<void>("/api/Auth/register", {
    ...jsonBody(body),
    skipAuth: true,
    errorMessage: "Unable to complete registration.",
  })
}
