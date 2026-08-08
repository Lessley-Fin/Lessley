import { useTranslation } from "react-i18next"

import { fintech } from "@/lib/fintech-styles"
import { formatFitPercent } from "@/lib/formatters"
import { ListRow } from "./ListRow"

export interface MatchingClubEntry {
  club_id?: string
  club_name?: string
  fit_score?: number
  hit_count?: number
  total_stores?: number
}

interface MatchingClubsListProps {
  clubs: MatchingClubEntry[]
  compact?: boolean
  limit?: number
}

export function MatchingClubsList({ clubs, compact = false, limit = 3 }: MatchingClubsListProps) {
  const { t } = useTranslation()
  const top = clubs.slice(0, limit)

  if (top.length === 0) {
    return (
      <p className={compact ? "text-xs text-slate-500" : "fintech-card-inset text-sm text-slate-600"}>
        {compact ? t("shared.matchingClubs.noneCompact") : t("shared.matchingClubs.noneFull")}
      </p>
    )
  }

  if (compact) {
    return (
      <div className="space-y-1.5">
        {top.map((club, idx) => (
          <div
            key={club.club_id ?? idx}
            className="flex items-center justify-between rounded-xl bg-white/60 px-3 py-2"
          >
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-slate-700">
                {idx + 1}. {club.club_name ?? club.club_id}
              </p>
              <p className="text-[10px] text-slate-400">
                {t("shared.matchingClubs.storesMatch", { hit: club.hit_count, total: club.total_stores })}
              </p>
            </div>
            {typeof club.fit_score === "number" ? (
              <span className={`${fintech.fitBadge} text-[10px]`}>{formatFitPercent(club.fit_score)}</span>
            ) : null}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {top.map((club, index) => (
        <ListRow key={club.club_id ?? index} variant="accent">
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-slate-800">
              {index + 1}. {club.club_name ?? club.club_id}
            </p>
            <p className="text-xs text-slate-500">
              {typeof club.fit_score === "number"
                ? `${t("shared.matchingClubs.fit", { percent: formatFitPercent(club.fit_score) })} · `
                : ""}
              {t("shared.matchingClubs.storesMatch", { hit: club.hit_count, total: club.total_stores })}
            </p>
          </div>
          {typeof club.fit_score === "number" ? (
            <span className={fintech.fitBadge}>{formatFitPercent(club.fit_score)}</span>
          ) : null}
        </ListRow>
      ))}
    </div>
  )
}
