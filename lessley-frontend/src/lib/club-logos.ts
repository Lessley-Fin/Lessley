import heverGiftCardLogo from "../../assets/hever_giftcard_logo.jpg"
import heverTeamimLogo from "../../assets/hever_teamim_logo.jpg"
import hotLogo from "../../assets/hot_logo.png"
import mastercardLogo from "../../assets/mastercard_logo.jpg"
import paisplusLogo from "../../assets/paisplus_logo.jpg"
import paisplusFoodChainsLogo from "../../assets/paisplus_food_chains_logo.png"
import paisplusNetworksLogo from "../../assets/paisplus_networks_logo.jpg"
import swishLogo from "../../assets/swish_logo.png"
import topcashLogo from "../../assets/topcash_logo.png"

export interface ClubLogo {
  src: string
  /**
   * How dark the artwork is, which is all the opacity needs to know. Light artwork
   * carries a normal watermark value; the navy and black scans tint a whole block
   * grey at that value, so they are toned down further.
   */
  tone: "light" | "dark"
}

/**
 * Club artwork keyed by the scraper `source_id` a deal carries — the same ids the
 * clubs collection is seeded with (`lessley-deals/data/seed/clubs.json`).
 *
 * Sources with no artwork yet — `behatsdaa` among them — are simply absent, so
 * every caller has to tolerate a miss rather than fall back to a placeholder.
 */
const LOGOS_BY_SOURCE_ID: Record<string, ClubLogo> = {
  hever_gift_card_company: { src: heverGiftCardLogo, tone: "light" },
  hever_teamim_card_store: { src: heverTeamimLogo, tone: "dark" },
  hot: { src: hotLogo, tone: "light" },
  mastercard: { src: mastercardLogo, tone: "dark" },
  // The LLM scraper covers the same promotion under its own site id.
  mastercard_day: { src: mastercardLogo, tone: "dark" },
  paisplus: { src: paisplusLogo, tone: "light" },
  // A VIP tier is the same card at a better rate, so it reuses the artwork.
  paisplus_food_chains_regular: { src: paisplusFoodChainsLogo, tone: "dark" },
  paisplus_food_chains_vip: { src: paisplusFoodChainsLogo, tone: "dark" },
  paisplus_networks_regular: { src: paisplusNetworksLogo, tone: "dark" },
  paisplus_networks_vip: { src: paisplusNetworksLogo, tone: "dark" },
  // The un-suffixed ids predate the regular/vip split. No club record carries them
  // any more, but deals scraped before the split still do, and they render the same
  // card — so they stay mapped rather than showing up as the one blank in a stack.
  paisplus_food_chains: { src: paisplusFoodChainsLogo, tone: "dark" },
  paisplus_networks: { src: paisplusNetworksLogo, tone: "dark" },
  swish: { src: swishLogo, tone: "light" },
  topcash: { src: topcashLogo, tone: "light" },
}

/**
 * Normalise the id forms a deal can reach the UI with: the clubs collection
 * prefixes ids with `club_`, and the LLM scraper emits `llm:<site>` site ids
 * that hyphenate where the native adapters use underscores.
 */
function normalizeId(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/^llm:/, "")
    .replace(/^club_/, "")
    .replace(/-/g, "_")
}

/**
 * The club artwork for a deal, or `undefined` when that source has none. Pass
 * whichever ids the deal carries — `source_id` wins, `club_id` covers records
 * where only the club is stamped.
 */
export function getClubLogo(sourceId?: string | null, clubId?: string | null): ClubLogo | undefined {
  for (const candidate of [sourceId, clubId]) {
    if (!candidate) continue
    const logo = LOGOS_BY_SOURCE_ID[normalizeId(candidate)]
    if (logo) return logo
  }
  return undefined
}
