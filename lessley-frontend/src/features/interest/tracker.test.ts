import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }))

vi.mock("@/lib/api-client", () => ({
  apiFetch,
  jsonBody: (data: unknown) => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }),
}))

import {
  BUFFER_CAP,
  FLUSH_INTERVAL_MS,
  __bufferedForTests,
  __resetTrackerForTests,
  track,
} from "./tracker"

function sentEvents(callIndex = 0) {
  const init = apiFetch.mock.calls[callIndex][1] as RequestInit
  return JSON.parse(init.body as string).events as Array<{ entityId: string; action: string }>
}

function hide() {
  Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true })
  document.dispatchEvent(new Event("visibilitychange"))
}

function show() {
  Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true })
  document.dispatchEvent(new Event("visibilitychange"))
}

describe("interest tracker", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    apiFetch.mockReset()
    apiFetch.mockResolvedValue({})
    window.sessionStorage.clear()
    __resetTrackerForTests()
  })

  afterEach(() => {
    __resetTrackerForTests()
    vi.useRealTimers()
  })

  it("buffers without sending anything", () => {
    track("deal", "deal-1", "impression")
    track("deal", "deal-1", "open")

    expect(apiFetch).not.toHaveBeenCalled()
    expect(__bufferedForTests()).toHaveLength(2)
  })

  it("does not flush on a full-ish buffer — only the timer sends", () => {
    // The gateway's rate limiter is global per user, so a burst of flushes competes with the
    // screen's own requests. Twenty events must still be zero requests.
    for (let i = 0; i < 20; i++) track("deal", `deal-${i}`, "impression")

    expect(apiFetch).not.toHaveBeenCalled()

    vi.advanceTimersByTime(FLUSH_INTERVAL_MS - 1)
    expect(apiFetch).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1)
    expect(apiFetch).toHaveBeenCalledTimes(1)
  })

  it("sends at most one request per interval no matter how fast events arrive", () => {
    for (let i = 0; i < 200; i++) track("deal", `deal-${i}`, "impression")

    vi.advanceTimersByTime(FLUSH_INTERVAL_MS)

    expect(apiFetch).toHaveBeenCalledTimes(1)
    expect(sentEvents()).toHaveLength(50) // the gateway's batch ceiling
  })

  it("posts to the events endpoint with keepalive", () => {
    track("deal", "deal-1", "redirect", { surface: "hot", position: 3 })
    vi.advanceTimersByTime(FLUSH_INTERVAL_MS)

    expect(apiFetch).toHaveBeenCalledTimes(1)
    const [path, init] = apiFetch.mock.calls[0] as [string, RequestInit]
    expect(path).toBe("/api/v1/deals/events")
    expect(init.keepalive).toBe(true)

    const [event] = sentEvents()
    expect(event).toMatchObject({ entityId: "deal-1", action: "redirect" })
  })

  it("flushes when the tab is hidden", () => {
    track("deal", "deal-1", "coupon_copy")
    expect(apiFetch).not.toHaveBeenCalled()

    hide()

    expect(apiFetch).toHaveBeenCalledTimes(1)
    expect(sentEvents()).toHaveLength(1)
  })

  it("does not flush when the tab becomes visible again", () => {
    track("deal", "deal-1", "impression")
    show()

    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("drops the oldest events past the cap", () => {
    for (let i = 0; i < BUFFER_CAP + 10; i++) track("deal", `deal-${i}`, "impression")

    const buffered = __bufferedForTests()
    expect(buffered).toHaveLength(BUFFER_CAP)
    // The newest survive: they are the ones still on screen.
    expect(buffered[0].entityId).toBe("deal-10")
    expect(buffered[buffered.length - 1].entityId).toBe(`deal-${BUFFER_CAP + 9}`)
  })

  it("never surfaces a failed flush", async () => {
    apiFetch.mockRejectedValue(new Error("gateway down"))
    track("deal", "deal-1", "impression")

    expect(() => vi.advanceTimersByTime(FLUSH_INTERVAL_MS)).not.toThrow()
    await vi.runOnlyPendingTimersAsync()

    expect(apiFetch).toHaveBeenCalledTimes(1)
  })

  it("reuses one session id per tab", () => {
    track("deal", "deal-1", "impression")
    track("deal", "deal-2", "impression")

    const buffered = __bufferedForTests()
    expect(buffered[0].sessionId).toBe(buffered[1].sessionId)
    expect(buffered[0].sessionId).toBeTruthy()
  })

  it("ignores an event with no entity id", () => {
    track("deal", "", "impression")
    expect(__bufferedForTests()).toHaveLength(0)
  })
})
