import { useTranslation } from "react-i18next"

import { MatchingClubsList, type MatchingClubEntry } from "@/components/shared/MatchingClubsList"
import { MissedSavingsList } from "@/components/shared/MissedSavingsList"
import { DealCard } from "@/features/deal-finder/components/DealCard"
import { useDealById } from "@/features/deal-finder/hooks"
import { useClubs } from "@/features/clubs/hooks"
import { fintech } from "@/lib/fintech-styles"
import type { ClubDto } from "@/lib/types"
import type { NotificationDto } from "../notificationTypes"

function tryParseJson(data: string | null): unknown {
  if (!data) return null
  try {
    return JSON.parse(data)
  } catch {
    return null
  }
}

function CategoriesDetail({ categories }: { categories: string[] }) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap gap-1.5">
      {categories.map((cat) => (
        <span
          key={cat}
          className="rounded-md bg-white/60 px-2 py-0.5 text-[10px] font-medium text-slate-500"
        >
          {t(`categories.${cat}`, { defaultValue: cat.replace(/_/g, " ").toLowerCase() })}
        </span>
      ))}
    </div>
  )
}

function DealDetail({ dealId, clubs }: { dealId: string; clubs: ClubDto[] }) {
  const { t } = useTranslation()
  const { data, isLoading } = useDealById(dealId)

  if (isLoading) {
    return <div className="h-20 animate-pulse rounded-2xl bg-slate-100" />
  }

  if (!data) {
    return (
      <p className="text-xs text-slate-400">
        {t("notifications.detail.deal")} · {dealId}
      </p>
    )
  }

  return <DealCard item={data} clubs={clubs} />
}

interface NotificationDetailProps {
  item: NotificationDto
}

export function NotificationDetail({ item }: NotificationDetailProps) {
  const { t } = useTranslation()
  const parsed = tryParseJson(item.data)
  const { data: clubs = [] } = useClubs()

  return (
    <div className="mt-3 space-y-2 rounded-2xl bg-secondary p-3">
      {item.calcType === "missed-savings" && Array.isArray(parsed) ? (
        <>
          <p className={fintech.sectionEyebrow}>{t("notifications.detail.missedSavingsAnalysis")}</p>
          <MissedSavingsList compact items={parsed} clubs={clubs} limit={3} />
        </>
      ) : item.calcType === "matching-clubs" && parsed && typeof parsed === "object" ? (
        <>
          <p className={fintech.sectionEyebrow}>{t("notifications.detail.clubRecommendations")}</p>
          <MatchingClubsList
            compact
            clubs={((parsed as { recommendations?: MatchingClubEntry[] }).recommendations) ?? []}
            limit={3}
          />
        </>
      ) : null}

      {item.dealId ? (
        <>
          <p className={fintech.sectionEyebrow}>{t("notifications.detail.deal")}</p>
          <DealDetail dealId={item.dealId} clubs={clubs} />
        </>
      ) : null}

      {item.categories && item.categories.length > 0 ? (
        <>
          <p className={fintech.sectionEyebrow}>{t("notifications.detail.categories")}</p>
          <CategoriesDetail categories={item.categories} />
        </>
      ) : null}

      {!item.calcType && !item.dealId && (!item.categories || item.categories.length === 0) ? (
        <p className="text-xs text-slate-500">{t("notifications.detail.noAdditionalDetails")}</p>
      ) : null}
    </div>
  )
}
