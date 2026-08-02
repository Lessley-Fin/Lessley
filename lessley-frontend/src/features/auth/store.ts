import { create } from "zustand"
import {
  SESSION_KEYS,
  clearSession,
  getAccessToken,
  getEmailFromToken,
  getRefreshToken,
  isAuthenticated as checkStoredAuth,
  storeSession,
  type SessionData,
} from "@/lib/auth"

interface AuthState {
  isAuthenticated: boolean
  accessToken: string | null
  refreshToken: string | null
  username: string
  userId: string
  email: string

  initialize: () => void
  login: (session: SessionData) => void
  logout: () => void
  setProfile: (profile: {
    username: string
    userId: string
    email: string
  }) => void
  setAccessToken: (token: string) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  accessToken: null,
  refreshToken: null,
  username: "User",
  userId: "",
  email: "",

  initialize: () => {
    const authenticated = checkStoredAuth()
    if (!authenticated) return

    const accessToken = getAccessToken()
    const refreshToken = getRefreshToken()
    const email =
      localStorage.getItem(SESSION_KEYS.email) ??
      (accessToken ? getEmailFromToken(accessToken) : "")

    set({
      isAuthenticated: true,
      accessToken,
      refreshToken,
      username: localStorage.getItem(SESSION_KEYS.username) ?? "User",
      userId: localStorage.getItem(SESSION_KEYS.userId) ?? "",
      email,
    })
  },

  login: (session: SessionData) => {
    storeSession(session)

    set({
      isAuthenticated: true,
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      username: session.username ?? "User",
      userId: session.userId ?? "",
      email: session.email ?? "",
    })
  },

  logout: () => {
    clearSession()
    set({
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      username: "User",
      userId: "",
      email: "",
    })
  },

  setProfile: ({ username, userId, email }) => {
    localStorage.setItem(SESSION_KEYS.username, username)
    localStorage.setItem(SESSION_KEYS.userId, userId)
    localStorage.setItem(SESSION_KEYS.email, email)
    set({ username, userId, email })
  },

  setAccessToken: (token: string) => {
    localStorage.setItem(SESSION_KEYS.accessToken, token)
    set({ accessToken: token })
  },
}))
