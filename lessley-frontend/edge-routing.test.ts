import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

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
 *
 * Lives at the repo root rather than under src/ because it reads files with node:fs. Files in
 * src/ are compiled by tsconfig.app.json, which has no node types (that would break
 * `npm run build`); this one is covered by tsconfig.node.json alongside vite.config.ts.
 */

const HERE = path.dirname(fileURLToPath(import.meta.url))
const CADDYFILE = path.resolve(HERE, "../lessley-cd/Caddyfile")
const VITE_CONFIG = path.resolve(HERE, "vite.config.ts")

function personalizationPrefixesInCaddyfile(): string[] {
  const caddyfile = readFileSync(CADDYFILE, "utf8")
  const matcher = caddyfile.match(/^\s*@personalization\s+path\s+(.+)$/m)
  expect(matcher, "no `@personalization path ...` matcher found in the Caddyfile").not.toBeNull()

  return matcher![1]
    .trim()
    .split(/\s+/)
    .map((prefix: string) => prefix.replace(/\/\*$/, ""))
    .sort()
}

function personalizationPrefixesInViteConfig(): string[] {
  const config = readFileSync(VITE_CONFIG, "utf8")
  return [...config.matchAll(/'([^']+)':\s*personalizationProxy/g)]
    .map((match: RegExpMatchArray) => match[1])
    .sort()
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
