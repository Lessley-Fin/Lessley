import type { ClubDto } from "@/lib/types"

/**
 * A loadable card sold at two rates carries one club id per rate in the deals
 * collection (`club_paisplus_networks_regular` / `_vip`) while the clubs collection
 * holds only the un-suffixed parent. Stripping the tier is what lets a deal on
 * either rung resolve back to the one club record — and to the one logo.
 */
const TIER_SUFFIXES = ["_regular", "_vip"]

/**
 * Reduces the id forms a club can reach the UI with to one comparable key: the
 * clubs collection prefixes ids with `club_`, the LLM scraper emits `llm:<site>`
 * site ids that hyphenate where the native adapters use underscores, and a deal
 * may carry either the source id or the club id.
 */
export function normalizeClubId(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/^llm:/, "")
    .replace(/^club_/, "")
    .replace(/-/g, "_")
}

/** The normalised id with any tier suffix removed, so both rungs collapse to the parent. */
function withoutTier(normalized: string): string {
  const suffix = TIER_SUFFIXES.find((s) => normalized.endsWith(s))
  return suffix ? normalized.slice(0, -suffix.length) : normalized
}

/**
 * The club's display name for whichever ids a deal carries. Falls back to the raw
 * id rather than to an empty string: an unrecognised club still has to render as
 * *something*, and the id at least says which source the deal came from.
 *
 * Matching runs widest-last — exact id, then normalised, then tier-stripped — so a
 * genuine `club_paisplus` never gets answered by the Networks card's record.
 */
export function resolveClubName(
  clubs: ClubDto[],
  clubId?: string | null,
  sourceId?: string | null,
): string | null {
  const candidates = [clubId, sourceId].filter((c): c is string => !!c?.trim())
  if (candidates.length === 0) return null

  for (const candidate of candidates) {
    const exact = clubs.find((c) => c.id === candidate)
    if (exact) return exact.name
  }

  for (const candidate of candidates) {
    const key = normalizeClubId(candidate)
    const hit = clubs.find((c) => normalizeClubId(c.id) === key)
    if (hit) return hit.name
  }

  for (const candidate of candidates) {
    const key = withoutTier(normalizeClubId(candidate))
    const hit = clubs.find((c) => withoutTier(normalizeClubId(c.id)) === key)
    if (hit) return hit.name
  }

  return candidates[0]
}
