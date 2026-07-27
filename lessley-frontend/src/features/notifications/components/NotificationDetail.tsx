import { MatchingClubsList, type MatchingClubEntry } from "@/components/shared/MatchingClubsList"
import { MissedSavingsList } from "@/components/shared/MissedSavingsList"
import { DealCard } from "@/features/deal-finder/components/DealCard"
import { useDealById } from "@/features/deal-finder/hooks"
import { fintech } from "@/lib/fintech-styles"
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
  return (
    <div className="flex flex-wrap gap-1.5">
      {categories.map((cat) => (
        <span
          key={cat}
          className="rounded-md bg-white/60 px-2 py-0.5 text-[10px] font-medium text-slate-500"
        >
          {cat.replace(/_/g, " ").toLowerCase()}
        </span>
      ))}
    </div>
  )
}

function DealDetail({ dealId }: { dealId: string }) {
  const { data, isLoading } = useDealById(dealId)

  if (isLoading) {
    return <div className="h-20 animate-pulse rounded-2xl bg-slate-100" />
  }

  if (!data) {
    return <p className="text-xs text-slate-400">Deal · {dealId}</p>
  }

  return <DealCard item={data} />
}

interface NotificationDetailProps {
  item: NotificationDto
}

export function NotificationDetail({ item }: NotificationDetailProps) {
  const parsed = tryParseJson(item.data)

  return (
    <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
      {item.calcType === "missed-savings" && Array.isArray(parsed) ? (
        <>
          <p className={fintech.sectionEyebrow}>Missed savings analysis</p>
          <MissedSavingsList compact items={parsed} limit={3} />
        </>
      ) : item.calcType === "matching-clubs" && parsed && typeof parsed === "object" ? (
        <>
          <p className={fintech.sectionEyebrow}>Club recommendations</p>
          <MatchingClubsList
            compact
            clubs={((parsed as { recommendations?: MatchingClubEntry[] }).recommendations) ?? []}
            limit={3}
          />
        </>
      ) : null}

      {item.dealId ? (
        <>
          <p className={fintech.sectionEyebrow}>Deal</p>
          <DealDetail dealId={item.dealId} />
        </>
      ) : null}

      {item.categories && item.categories.length > 0 ? (
        <>
          <p className={fintech.sectionEyebrow}>Categories</p>
          <CategoriesDetail categories={item.categories} />
        </>
      ) : null}

      {!item.calcType && !item.dealId && (!item.categories || item.categories.length === 0) ? (
        <p className="text-xs text-slate-500">No additional details.</p>
      ) : null}
    </div>
  )
}
