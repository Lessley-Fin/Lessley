import { describe, it, expect, beforeEach, vi } from "vitest"

vi.mock("@/lib/api-client", () => ({ apiFetch: vi.fn() }))
vi.mock("@/lib/auth", () => ({ logoutRequest: vi.fn() }))

import { useAuthStore } from "./store"
import { apiFetch } from "@/lib/api-client"
import { logoutRequest } from "@/lib/auth"

const mockedApiFetch = vi.mocked(apiFetch)

describe("useAuthStore", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      status: "loading",
      isAuthenticated: false,
      username: "User",
      userId: "",
      email: "",
    })
  })

  it("holds no tokens in state (cookie-based auth)", () => {
    const state = useAuthStore.getState() as unknown as Record<string, unknown>
    expect(state.accessToken).toBeUndefined()
    expect(state.refreshToken).toBeUndefined()
  })

  it("login sets authenticated state", () => {
    useAuthStore.getState().login({ username: "Yoav", userId: "yoav@test.com", email: "yoav@test.com" })

    const state = useAuthStore.getState()
    expect(state.status).toBe("authenticated")
    expect(state.isAuthenticated).toBe(true)
    expect(state.username).toBe("Yoav")
    expect(state.email).toBe("yoav@test.com")
  })

  it("logout clears state and calls the server", () => {
    useAuthStore.getState().login({ username: "Yoav", userId: "y@test.com", email: "y@test.com" })

    useAuthStore.getState().logout()

    const state = useAuthStore.getState()
    expect(state.status).toBe("unauthenticated")
    expect(state.isAuthenticated).toBe(false)
    expect(state.username).toBe("User")
    expect(logoutRequest).toHaveBeenCalled()
  })

  it("initialize authenticates when the profile probe succeeds", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      email: "me@test.com",
      userName: "Me",
      roles: [],
      clubs: [],
      tags: [],
      mutedTags: [],
      matchLevel: null,
    })

    await useAuthStore.getState().initialize()

    const state = useAuthStore.getState()
    expect(state.status).toBe("authenticated")
    expect(state.isAuthenticated).toBe(true)
    expect(state.email).toBe("me@test.com")
    expect(state.username).toBe("Me")
  })

  it("initialize marks unauthenticated when the probe fails", async () => {
    mockedApiFetch.mockRejectedValueOnce(new Error("401"))

    await useAuthStore.getState().initialize()

    expect(useAuthStore.getState().status).toBe("unauthenticated")
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it("setProfile updates profile fields", () => {
    useAuthStore.getState().setProfile({
      username: "New",
      userId: "new@test.com",
      email: "new@test.com",
    })

    const state = useAuthStore.getState()
    expect(state.username).toBe("New")
    expect(state.email).toBe("new@test.com")
  })
})
