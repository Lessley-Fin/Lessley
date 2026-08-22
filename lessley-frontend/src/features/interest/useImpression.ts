import { useEffect, useRef } from "react"

import { track, type InterestEntityType } from "./tracker"

/** ≥50% of the card visible counts as "on screen". */
const VISIBLE_RATIO = 0.5

/** ...and it has to stay there this long. A card scrolled past is not an impression. */
const DWELL_MS = 1000

/**
 * One impression per entity per page load. Module-level rather than per-component because the
 * same deal appears on more than one surface, and re-mounting a card is not a new viewing.
 */
const seen = new Set<string>()

interface ImpressionOptions {
  surface?: string
  position?: number
}

/**
 * Fires an `impression` once the returned ref's element has been at least half visible for a
 * continuous second.
 *
 * Never on render, which is the whole point: `DealFinderTab` re-renders on every keystroke
 * across three inputs, and both lists render items far below the fold. Counting renders would
 * make the impression denominator meaningless and, with it, the engagement rate the ranking
 * is built on.
 */
export function useImpression<T extends Element>(
  entityType: InterestEntityType,
  entityId: string | undefined,
  options: ImpressionOptions = {},
) {
  const ref = useRef<T | null>(null)
  const { surface, position } = options

  useEffect(() => {
    const element = ref.current
    if (!element || !entityId) return

    const key = `${entityType}:${entityId}`
    if (seen.has(key)) return

    // jsdom without a polyfill, and very old browsers. Silently not tracking is correct —
    // an impression we cannot measure is better absent than guessed.
    if (typeof IntersectionObserver === "undefined") return

    let dwell: ReturnType<typeof setTimeout> | undefined

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[entries.length - 1]
        if (!entry) return

        if (entry.isIntersecting && entry.intersectionRatio >= VISIBLE_RATIO) {
          if (dwell !== undefined) return
          dwell = setTimeout(() => {
            dwell = undefined
            if (seen.has(key)) return
            seen.add(key)
            track(entityType, entityId, "impression", { surface, position })
            observer.disconnect()
          }, DWELL_MS)
        } else if (dwell !== undefined) {
          clearTimeout(dwell)
          dwell = undefined
        }
      },
      { threshold: [0, VISIBLE_RATIO, 1] },
    )

    observer.observe(element)

    return () => {
      if (dwell !== undefined) clearTimeout(dwell)
      observer.disconnect()
    }
    // A position change (paging) restarts the dwell, which is correct: the list under the
    // user changed, so a card that was half-watched was not watched.
  }, [entityType, entityId, surface, position])

  return ref
}

/** Test seam: forgets which entities have already been counted. */
export function __resetImpressionsForTests(): void {
  seen.clear()
}
