import { readFileSync } from "node:fs"
import path from "node:path"

import { describe, expect, it } from "vitest"

/**
 * The Vite dev proxy stands in for Caddy: in production Caddy decides which prefixes go to
 * Personalization and which fall through to the Gateway, and in local dev the Vite proxy has
 * to make exactly the same decision. When the two drift, a route works in production and
 * 404s locally (or worse, the reverse).
 *
 * This actually happened: clubs moved from Personalization to the Gateway's ClubController,
 * the Caddyfile was updated and vite.config.ts was not, so `/api/v1/clubs` kept being sent
 * to Personalization — which has no such route — and the client got a 404 in dev only.
 */

const ROOT = path.resolve(__dirname, "../..")
const CADDYFILE = path.resolve(ROOT, "../lessley-cd/Caddyfile")
const VITE_CONFIG = path.resolve(ROOT, "vite.config.ts")

function personalizationPrefixesInCaddyfile(): string[] {
  const caddyfile = readFileSync(CADDYFILE, "utf8")
  const matcher = caddyfile.match(/^\s*@personalization\s+path\s+(.+)$/m)
  expect(matcher, "no `@personalization path ...` matcher found in the Caddyfile").not.toBeNull()

  return matcher![1]
    .trim()
    .split(/\s+/)
    .map((prefix) => prefix.replace(/\/\*$/, ""))
    .sort()
}

function personalizationPrefixesInViteConfig(): string[] {
  const config = readFileSync(VITE_CONFIG, "utf8")
  return [...config.matchAll(/'([^']+)':\s*personalizationProxy/g)].map((m) => m[1]).sort()
}

describe("dev proxy mirrors the production edge", () => {
  it("routes exactly the same prefixes to Personalization as the Caddyfile does", () => {
    expect(personalizationPrefixesInViteConfig()).toEqual(personalizationPrefixesInCaddyfile())
  })

  it("does not send /api/v1/clubs to Personalization — the Gateway owns clubs", () => {
    expect(personalizationPrefixesInViteConfig()).not.toContain("/api/v1/clubs")
    expect(personalizationPrefixesInCaddyfile()).not.toContain("/api/v1/clubs")
  })
})
