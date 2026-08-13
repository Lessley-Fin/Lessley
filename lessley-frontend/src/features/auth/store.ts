import { create } from "zustand"

import { apiFetch } from "@/lib/api-client"
import { logoutRequest } from "@/lib/auth"
import type { MeResponse } from "@/features/user/api"

// "loading" until the initial server probe resolves — route guards must wait for it so a
// page reload (where auth lives only in cookies) doesn't bounce the user to /login.
export type AuthStatus = "loading" | "authenticated" | "unauthenticated"

interface Profile {
  username: string
  userId: string
  email: string
}

interface AuthState extends Profile {
  status: AuthStatus
  isAuthenticated: boolean
  // RegisterWizard logs the user in before its Banking step so BankingStep can call the
  // authenticated connect-bank endpoint — this keeps GuestRoute from bouncing them out of
  // /register to the app in that gap. Cleared once the wizard finishes or the user logs out.
  registrationInProgress: boolean

  initialize: () => Promise<void>
  login: (profile: Profile) => void
  logout: () => void
  setProfile: (profile: Profile) => void
  setRegistrationInProgress: (value: boolean) => void
}

const ANON = {
  status: "unauthenticated" as AuthStatus,
  isAuthenticated: false,
  username: "User",
  userId: "",
  email: "",
  registrationInProgress: false,
}

export const useAuthStore = create<AuthState>((set) => ({
  status: "loading",
  isAuthenticated: false,
  username: "User",
  userId: "",
  email: "",
  registrationInProgress: false,

  // Probe the server: if the auth cookie is valid (or refreshable) we get the profile.
  initialize: async () => {
    set({ status: "loading" })
    try {
      const profile = await apiFetch<MeResponse>("/api/v1/User/me")
      const email = profile.email?.trim().toLowerCase() ?? ""
      set({
        status: "authenticated",
        isAuthenticated: true,
        username: profile.userName || "User",
        userId: email,
        email,
      })
    } catch {
      set({ ...ANON })
    }
  },

  login: ({ username, userId, email }) =>
    set({ status: "authenticated", isAuthenticated: true, username, userId, email }),

  logout: () => {
    void logoutRequest()
    set({ ...ANON })
  },

  setProfile: ({ username, userId, email }) => set({ username, userId, email }),
  setRegistrationInProgress: (registrationInProgress) => set({ registrationInProgress }),
}))
