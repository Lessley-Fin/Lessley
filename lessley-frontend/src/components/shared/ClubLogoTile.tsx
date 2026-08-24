import { getClubLogo } from "@/lib/club-logos"
import { emojiForClub } from "@/lib/constants"
import { cn } from "@/lib/utils"

interface ClubLogoTileProps {
  /** The club record's id — `club_`-prefixed, which `getClubLogo` normalises away. */
  clubId: string
  /** Only used to pick the emoji fallback for a club with no artwork. */
  clubName: string
  /** `band` fills the top of a selection card; `inline` sits inside a chip. */
  variant?: "band" | "inline"
  className?: string
}

/**
 * The club's artwork on a white plate, for the two places a user *picks* clubs
 * (registration and settings). Unlike the watermark in StackSteps this shows the
 * logo at full opacity, so it needs a plate: most of the scans are opaque JPEGs of
 * physical cards, and dropping one straight onto the tinted card fill reads as a
 * pasted-on rectangle. White is also what the wordmark PNGs (swish, topcash, hot)
 * were cut against, so those blend into the plate instead of showing a seam.
 *
 * Artwork aspect ratios run from 1:1 wordmarks to 1.85:1 card scans, so the plate
 * fixes the height and lets `object-contain` centre each one at its own width —
 * uniform rows, nothing cropped or stretched.
 *
 * `behatsdaa` has no artwork (see club-logos.ts), so the emoji stands in. In `band`
 * it keeps the plate, because a short card in a grid of tall ones is worse than a
 * plain-looking one; in `inline` it renders bare, exactly as the chips did before.
 */
export function ClubLogoTile({ clubId, clubName, variant = "band", className }: ClubLogoTileProps) {
  const logo = getClubLogo(clubId)
  const isBand = variant === "band"

  if (!logo) {
    const emoji = (
      <span aria-hidden className={isBand ? "text-2xl" : "text-sm leading-none"}>
        {emojiForClub(clubName)}
      </span>
    )
    if (!isBand) return emoji
    return (
      <span
        className={cn(
          "flex h-14 w-full items-center justify-center rounded-xl bg-white ring-1 ring-black/5",
          className,
        )}
      >
        {emoji}
      </span>
    )
  }

  return (
    <span
      className={cn(
        "flex items-center justify-center overflow-hidden bg-white ring-1 ring-black/5",
        isBand ? "h-14 w-full rounded-xl p-2" : "h-5 max-w-10 rounded px-0.5",
        className,
      )}
    >
      {/* Decorative: every caller renders the club name next to this. */}
      <img
        src={logo.src}
        alt=""
        aria-hidden
        loading="lazy"
        className="h-full w-auto max-w-full select-none object-contain"
      />
    </span>
  )
}
