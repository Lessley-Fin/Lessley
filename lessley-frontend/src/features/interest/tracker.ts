import { apiFetch, jsonBody } from "@/lib/api-client"

export type InterestEntityType = "deal" | "store"

export type InterestAction =
  | "impression"
  | "search_hit"
  | "open"
  | "coupon_copy"
  | "redirect"

export interface InterestEvent {
  eventId: string
  entityType: InterestEntityType
  entityId: string
  action: InterestAction
  sessionId: string
  surface: string
  position?: number
  ts: string
}

interface TrackOptions {
  /** Which screen the event came from, e.g. "hot" or "deal_finder". */
  surface?: string
  /** 0-based rank in the list it came from. Logged for later position debiasing. */
  position?: number
}

export const FLUSH_INTERVAL_MS = 5000

/**
 * Ceiling on unsent events. Reached only by a user scrolling faster than the flush interval;
 * the oldest go first, because the newest are the ones still on screen.
 */
export const BUFFER_CAP = 200

/** Matches the gateway's own batch ceiling — a larger POST is rejected with a 400. */
const MAX_BATCH = 50

const SESSION_KEY = "lessley.interest.session"

let buffer: InterestEvent[] = []
let timer: ReturnType<typeof setInterval> | undefined
let listening = false

function uuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  // jsdom and older Safari have no randomUUID. Uniqueness only has to hold within one
  // client's stream — the server's unique index is what actually enforces it.
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

/**
 * Per-tab session id. In sessionStorage rather than localStorage so two tabs are two
 * sessions, which is what a session is supposed to mean.
 */
export function sessionId(): string {
  try {
    const existing = window.sessionStorage.getItem(SESSION_KEY)
    if (existing) return existing
    const created = uuid()
    window.sessionStorage.setItem(SESSION_KEY, created)
    return created
  } catch {
    // Private mode / storage disabled — an ephemeral id still groups this page's events.
    return uuid()
  }
}

/**
 * Buffers one event. Never sends — see {@link flush}.
 */
export function track(
  entityType: InterestEntityType,
  entityId: string,
  action: InterestAction,
  options: TrackOptions = {},
): void {
  if (!entityId) return

  buffer.push({
    eventId: uuid(),
    entityType,
    entityId,
    action,
    sessionId: sessionId(),
    surface: options.surface ?? "",
    ...(options.position === undefined ? {} : { position: options.position }),
    ts: new Date().toISOString(),
  })

  if (buffer.length > BUFFER_CAP) {
    buffer = buffer.slice(buffer.length - BUFFER_CAP)
  }

  start()
}

/**
 * Sends everything buffered.
 *
 * Called from the timer and from `visibilitychange` only — deliberately NOT when the buffer
 * fills. The gateway's rate limiter is *global* per user (20 requests / 5s) and named policies
 * stack on top of it rather than replacing it, so a telemetry flush competes with the app's
 * real requests. Firing on a full buffer would let a fast scroll issue a burst and 429 the
 * screen the user is actually looking at; a timer cannot exceed one request per interval no
 * matter how fast events arrive.
 */
export async function flush(): Promise<void> {
  if (buffer.length === 0) return

  const events = buffer.slice(0, MAX_BATCH)
  buffer = buffer.slice(events.length)

  try {
    await apiFetch("/api/v1/deals/events", {
      ...jsonBody({ events }),
      // Survives the page being torn down mid-request, which is exactly when a
      // visibilitychange flush happens.
      keepalive: true,
      skipAuth: true,
    })
  } catch {
    // Dropped on purpose. Telemetry must never surface to the user, and re-queueing a failing
    // batch would grow the buffer against a backend that is already refusing it.
  }
}

/** Starts the timer and the visibility listener. Idempotent; safe to call on every track. */
function start(): void {
  if (timer === undefined) {
    timer = setInterval(() => void flush(), FLUSH_INTERVAL_MS)
  }

  if (!listening && typeof document !== "undefined") {
    document.addEventListener("visibilitychange", onVisibilityChange)
    listening = true
  }
}

function onVisibilityChange(): void {
  // Only on the way out. A tab becoming visible has nothing new to report, and the flush
  // would land in the same window as the render's own requests.
  if (document.visibilityState === "hidden") void flush()
}

/** Test seam: drops the buffer and stops the timer. Not used by the app. */
export function __resetTrackerForTests(): void {
  buffer = []
  if (timer !== undefined) {
    clearInterval(timer)
    timer = undefined
  }
  if (listening && typeof document !== "undefined") {
    document.removeEventListener("visibilitychange", onVisibilityChange)
    listening = false
  }
}

/** Test seam: what is waiting to be sent. */
export function __bufferedForTests(): readonly InterestEvent[] {
  return buffer
}
