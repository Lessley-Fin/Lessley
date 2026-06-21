import { describe, it, expect, beforeEach } from "vitest"
import { useAuthStore } from "./store"

describe("useAuthStore", () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      username: "User",
      userId: "",
      email: "",
    })
  })

  it("starts unauthenticated", () => {
    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(false)
    expect(state.accessToken).toBeNull()
  })

  it("login sets auth state and writes to localStorage", () => {
    useAuthStore.getState().login({
      accessToken: "test-access",
      refreshToken: "test-refresh",
      username: "Yoav",
      userId: "yoav@test.com",
      email: "yoav@test.com",
    })

    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(true)
    expect(state.accessToken).toBe("test-access")
    expect(state.refreshToken).toBe("test-refresh")
    expect(state.username).toBe("Yoav")
    expect(state.email).toBe("yoav@test.com")
    expect(localStorage.getItem("lessley_access_token")).toBe("test-access")
    expect(localStorage.getItem("lessley_poc_session")).toBe("active")
  })

  it("logout clears auth state and localStorage", () => {
    useAuthStore.getState().login({
      accessToken: "test-access",
      refreshToken: "test-refresh",
      username: "Yoav",
    })

    useAuthStore.getState().logout()

    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(false)
    expect(state.accessToken).toBeNull()
    expect(state.username).toBe("User")
    expect(localStorage.getItem("lessley_access_token")).toBeNull()
    expect(localStorage.getItem("lessley_poc_session")).toBeNull()
  })

  it("initialize hydrates from localStorage", () => {
    localStorage.setItem("lessley_poc_session", "active")
    localStorage.setItem("lessley_access_token", "stored-token")
    localStorage.setItem("lessley_refresh_token", "stored-refresh")
    localStorage.setItem("lessley_username", "StoredUser")
    localStorage.setItem("lessley_user_email", "stored@test.com")
    localStorage.setItem("lessley_user_id", "stored@test.com")

    useAuthStore.getState().initialize()

    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(true)
    expect(state.accessToken).toBe("stored-token")
    expect(state.username).toBe("StoredUser")
    expect(state.email).toBe("stored@test.com")
  })

  it("setProfile updates profile fields", () => {
    useAuthStore.getState().login({
      accessToken: "t",
      refreshToken: "r",
      username: "Old",
    })

    useAuthStore.getState().setProfile({
      username: "New",
      userId: "new@test.com",
      email: "new@test.com",
    })

    const state = useAuthStore.getState()
    expect(state.username).toBe("New")
    expect(state.email).toBe("new@test.com")
    expect(localStorage.getItem("lessley_username")).toBe("New")
  })

  it("setAccessToken updates token in state and localStorage", () => {
    useAuthStore.getState().setAccessToken("new-token")

    expect(useAuthStore.getState().accessToken).toBe("new-token")
    expect(localStorage.getItem("lessley_access_token")).toBe("new-token")
  })
})
