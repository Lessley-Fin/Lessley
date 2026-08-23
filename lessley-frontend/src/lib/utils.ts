import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function toggleArrayValue(current: string[], value: string): string[] {
  return current.includes(value) ? current.filter((v) => v !== value) : [...current, value]
}

export function getClubName(clubs: { id: string; name: string }[], clubId: string): string {
  return clubs.find((c) => c.id === clubId)?.name ?? clubId
}

/**
 * The club a scraped deal came from. Deals are tagged with the scraper's `source_id`
 * rather than the club's own id, so that is what the clubs list is searched on.
 * Falls back to the raw source id for a club the list doesn't carry.
 */
export function getClubNameBySource(
  clubs: { sourceId?: string | null; name: string }[],
  sourceId?: string | null,
): string | null {
  if (!sourceId) return null
  return clubs.find((c) => c.sourceId === sourceId)?.name ?? sourceId
}
