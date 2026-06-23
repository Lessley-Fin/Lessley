import { Lightbulb, Store, TrendingDown } from "lucide-react"

import { CLUBS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount, formatFitPercent } from "@/lib/formatters"
import type { NotificationDto } from "../notificationTypes"

function resolveClubName(clubId: string): string {
  return CLUBS.find((c) => c.id === clubId)?.name ?? clubId
}

function tryParseJson(data: string | null): unknown {
  if (!data) return null
  try {
    return JSON.parse(data)
  } catch {
    return null
  }
}

interface MissedSavingsItem {
  transaction_id?: string
  store_name?: string
  amount?: number
  mcc_description?: string
  missed_store_discont?: Array<{
    club_id?: string
    missed_store?: Array<{ store_name?: string }>
  }>
}

interface MatchingClubsData {
  recommendations?: Array<{
    club_id?: string
    club_name?: string
    fit_score?: number
    hit_count?: number
    total_stores?: number
  }>
}

function MissedSavingsDetail({ items }: { items: MissedSavingsItem[] }) {
  const relevant = items.filter((i) => (i.missed_store_discont?.length ?? 0) > 0).slice(0, 3)

  if (relevant.length === 0) {
    return <p className="text-xs text-slate-500">No missed savings found in this analysis.</p>
  }

  return (
    <div className="space-y-2">
      {relevant.map((item, idx) => {
        const topDiscount = item.missed_store_discont?.[0]
        const clubName = topDiscount?.club_id ? resolveClubName(topDiscount.club_id) : null
        const altStores = topDiscount?.missed_store?.slice(0, 3).map((s) => s.store_name).join(", ")

        return (
          <div key={item.transaction_id ?? idx} className="space-y-1.5 rounded-xl bg-white/60 p-3">
            <div className="flex items-center gap-2">
              <Store className="size-3.5 shrink-0 text-blue-500" />
              <p className="text-xs font-medium text-slate-700">
                {formatAmount(item.amount)} at {item.store_name ?? "Unknown"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <TrendingDown className="size-3.5 shrink-0 text-red-400" />
              <p className="text-xs text-slate-500">
                Savings available in {item.mcc_description ?? "this category"}
              </p>
            </div>
            {clubName ? (
              <div className="flex items-center gap-2">
                <Lightbulb className="size-3.5 shrink-0 text-emerald-500" />
                <p className="text-xs text-slate-500">
                  <span className="font-medium text-slate-600">{clubName}</span> had deals
                  {altStores ? ` at ${altStores}` : ""}
                </p>
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

function MatchingClubsDetail({ data }: { data: MatchingClubsData }) {
  const clubs = data.recommendations?.slice(0, 3) ?? []

  if (clubs.length === 0) {
    return <p className="text-xs text-slate-500">No club matches found.</p>
  }

  return (
    <div className="space-y-1.5">
      {clubs.map((club, idx) => (
        <div
          key={club.club_id ?? idx}
          className="flex items-center justify-between rounded-xl bg-white/60 px-3 py-2"
        >
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-slate-700">
              {idx + 1}. {club.club_name ?? club.club_id}
            </p>
            <p className="text-[10px] text-slate-400">
              {club.hit_count}/{club.total_stores} stores match
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
          <MissedSavingsDetail items={parsed as MissedSavingsItem[]} />
        </>
      ) : item.calcType === "matching-clubs" && parsed && typeof parsed === "object" ? (
        <>
          <p className={fintech.sectionEyebrow}>Club recommendations</p>
          <MatchingClubsDetail data={parsed as MatchingClubsData} />
        </>
      ) : null}

      {item.dealId ? (
        <p className="text-xs text-slate-400">Deal · {item.dealId}</p>
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
