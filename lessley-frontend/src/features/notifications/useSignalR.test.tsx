import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { queryKeys } from "@/lib/query-keys"

// Handlers the hook registers, captured so a test can play the server's part.
const handlers = new Map<string, (payload: unknown) => void>()
let reconnected: (() => void) | undefined

vi.mock("@microsoft/signalr", () => {
  class HubConnectionBuilder {
    withUrl() { return this }
    withAutomaticReconnect() { return this }
    configureLogging() { return this }
    build() {
      return {
        state: "Connected",
        on: (event: string, handler: (payload: unknown) => void) => handlers.set(event, handler),
        off: (event: string) => handlers.delete(event),
        onreconnected: (handler: () => void) => { reconnected = handler },
        onreconnecting: () => {},
        onclose: () => {},
        start: () => Promise.resolve(),
        stop: () => Promise.resolve(),
      }
    }
  }
  return {
    HubConnectionBuilder,
    HubConnectionState: { Disconnected: "Disconnected" },
    LogLevel: { Warning: 3 },
  }
})

vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }))
vi.mock("@/features/auth/store", () => ({
  useAuthStore: (selector: (s: { isAuthenticated: boolean }) => unknown) =>
    selector({ isAuthenticated: true }),
}))

const { useSignalR } = await import("./useSignalR")

function wrapper(client: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

describe("useSignalR — categories", () => {
  const spyOnInvalidate = (c: QueryClient) =>
    vi.spyOn(c, "invalidateQueries").mockResolvedValue(undefined)

  let client: QueryClient
  let invalidate: ReturnType<typeof spyOnInvalidate>

  beforeEach(() => {
    handlers.clear()
    reconnected = undefined
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    invalidate = spyOnInvalidate(client)
  })

  it("subscribes to the event name the gateway actually sends", async () => {
    renderHook(() => useSignalR(), { wrapper: wrapper(client) })

    // The string is a contract with UserTagService.NotifyCategoriesUpdatedAsync. A typo on
    // either side fails silently — the push lands nowhere and the screen just stays stale.
    await waitFor(() => expect(handlers.has("CategoriesUpdated")).toBe(true))
  })

  it("refreshes insights and profile when the server says categories changed", async () => {
    renderHook(() => useSignalR(), { wrapper: wrapper(client) })
    await waitFor(() => expect(handlers.has("CategoriesUpdated")).toBe(true))

    invalidate.mockClear()
    handlers.get("CategoriesUpdated")!({ timestamp: "2026-08-17T00:00:00Z", tags: ["GROCERIES"] })

    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.insights.all })
    // Tags ride on the profile too, so the settings screen would otherwise offer the old
    // list to mute against.
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.user.profile() })
  })

  it("shows no toast for a category refresh", async () => {
    // It is a cache signal, not news. The user did not ask for the weekly sweep and should
    // not be interrupted by it.
    const { toast } = await import("sonner")
    renderHook(() => useSignalR(), { wrapper: wrapper(client) })
    await waitFor(() => expect(handlers.has("CategoriesUpdated")).toBe(true))

    handlers.get("CategoriesUpdated")!({ timestamp: "2026-08-17T00:00:00Z", tags: [] })

    expect(toast.custom).not.toHaveBeenCalled()
  })

  it("refreshes on reconnect, since a push sent while offline reached nobody", async () => {
    renderHook(() => useSignalR(), { wrapper: wrapper(client) })
    await waitFor(() => expect(reconnected).toBeDefined())

    invalidate.mockClear()
    reconnected!()

    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.insights.all })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.notifications.all })
  })
})

vi.mock("sonner", () => ({ toast: Object.assign(vi.fn(), { custom: vi.fn(), dismiss: vi.fn() }) }))
