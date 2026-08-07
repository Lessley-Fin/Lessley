import { RefreshCw, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { emojiForClub } from "@/lib/constants"
import { formatFitPercent } from "@/lib/formatters"
import type { ClubRecommendation } from "@/lib/types"

interface TopClubMatchesSlideProps {
  clubs: ClubRecommendation[]
  onRecalculate: () => void
  isPending: boolean
}

export function TopClubMatchesSlide({ clubs, onRecalculate, isPending }: TopClubMatchesSlideProps) {
  return (
    <div className="flex h-[420px] flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-3">
        <span className="flex size-10 items-center justify-center rounded-full bg-accent">
          <Sparkles className="size-4 text-accent-foreground" aria-hidden />
        </span>
        <div className="flex-1">
          <p className="font-bold">Top club matches</p>
          <p className="text-xs text-muted-foreground">Ranked by store overlap with your spend</p>
        </div>
        <Button
          type="button"
          variant="pill"
          size="icon"
          aria-label="Recalculate matches"
          onClick={onRecalculate}
          disabled={isPending}
        >
          <RefreshCw className={isPending ? "animate-spin" : ""} aria-hidden />
        </Button>
      </div>
      {clubs.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          We need more transaction history to analyze club fit. Try recalculating or connect more accounts.
        </p>
      ) : (
        <ul className="no-scrollbar min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {clubs.map((club, i) => (
            <li key={club.club_id} className="rounded-2xl bg-secondary p-3">
              <div className="flex items-center gap-3">
                <span className="flex size-8 items-center justify-center rounded-full bg-card text-sm font-bold">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">
                    {emojiForClub(club.club_name)} {club.club_name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {club.hit_count}/{club.total_stores} stores match
                  </p>
                </div>
                <span className="inline-flex items-center rounded-full bg-accent px-2.5 py-0.5 text-xs font-semibold text-accent-foreground">
                  {formatFitPercent(club.fit_score)}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-card">
                <div
                  className="surface-teal h-full rounded-full"
                  style={{ width: `${Math.round(club.fit_score * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
