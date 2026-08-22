import { act, render } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const { track } = vi.hoisted(() => ({ track: vi.fn() }))

vi.mock("./tracker", () => ({ track }))

import { __resetImpressionsForTests, useImpression } from "./useImpression"

/**
 * jsdom has no IntersectionObserver, and a real one would not observe anything in a layout
 * engine with no layout. This stands in for it so the dwell rule itself can be asserted.
 */
class MockIntersectionObserver {
  static instances: MockIntersectionObserver[] = []

  private readonly callback: IntersectionObserverCallback
  disconnected = false

  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback
    MockIntersectionObserver.instances.push(this)
  }

  observe() {}
  unobserve() {}
  disconnect() {
    this.disconnected = true
  }
  takeRecords() {
    return []
  }

  /** Reports a visibility ratio to the hook under test. */
  emit(ratio: number) {
    this.callback(
      [{ isIntersecting: ratio > 0, intersectionRatio: ratio } as IntersectionObserverEntry],
      this as unknown as IntersectionObserver,
    )
  }

  static latest() {
    return MockIntersectionObserver.instances[MockIntersectionObserver.instances.length - 1]
  }
}

function Card({ id, position = 0 }: { id: string; position?: number }) {
  const ref = useImpression<HTMLDivElement>("deal", id, { surface: "hot", position })
  return <div ref={ref}>{id}</div>
}

describe("useImpression", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    track.mockReset()
    MockIntersectionObserver.instances = []
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver)
    __resetImpressionsForTests()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it("does not fire before a full second of visibility", () => {
    render(<Card id="deal-1" />)

    act(() => MockIntersectionObserver.latest().emit(0.6))

    act(() => void vi.advanceTimersByTime(999))
    expect(track).not.toHaveBeenCalled()

    act(() => void vi.advanceTimersByTime(1))
    expect(track).toHaveBeenCalledTimes(1)
    expect(track).toHaveBeenCalledWith("deal", "deal-1", "impression", {
      surface: "hot",
      position: 0,
    })
  })

  it("does not fire for a card scrolled past", () => {
    render(<Card id="deal-1" />)

    act(() => MockIntersectionObserver.latest().emit(0.6))
    act(() => void vi.advanceTimersByTime(500))
    act(() => MockIntersectionObserver.latest().emit(0))
    act(() => void vi.advanceTimersByTime(2000))

    expect(track).not.toHaveBeenCalled()
  })

  it("does not fire when the card is only barely on screen", () => {
    render(<Card id="deal-1" />)

    act(() => MockIntersectionObserver.latest().emit(0.2))
    act(() => void vi.advanceTimersByTime(2000))

    expect(track).not.toHaveBeenCalled()
  })

  it("fires once across re-renders", () => {
    const { rerender } = render(<Card id="deal-1" position={0} />)

    act(() => MockIntersectionObserver.latest().emit(0.6))
    act(() => void vi.advanceTimersByTime(1000))
    expect(track).toHaveBeenCalledTimes(1)

    // DealFinderTab re-renders on every keystroke; a re-render is not a new viewing.
    rerender(<Card id="deal-1" position={0} />)
    act(() => MockIntersectionObserver.latest().emit(0.6))
    act(() => void vi.advanceTimersByTime(2000))

    expect(track).toHaveBeenCalledTimes(1)
  })

  it("fires once per entity even when the same deal appears on two surfaces", () => {
    render(
      <>
        <Card id="deal-1" />
        <Card id="deal-1" />
      </>,
    )

    act(() => MockIntersectionObserver.instances.forEach((observer) => observer.emit(0.6)))
    act(() => void vi.advanceTimersByTime(2000))

    expect(track).toHaveBeenCalledTimes(1)
  })

  it("tracks a different deal separately", () => {
    render(
      <>
        <Card id="deal-1" />
        <Card id="deal-2" />
      </>,
    )

    act(() => MockIntersectionObserver.instances.forEach((observer) => observer.emit(0.6)))
    act(() => void vi.advanceTimersByTime(1000))

    expect(track).toHaveBeenCalledTimes(2)
  })

  it("does nothing without an IntersectionObserver", () => {
    vi.stubGlobal("IntersectionObserver", undefined)

    expect(() => render(<Card id="deal-1" />)).not.toThrow()
    act(() => void vi.advanceTimersByTime(5000))
    expect(track).not.toHaveBeenCalled()
  })
})
