import { Lightbulb, Store, TrendingDown } from "lucide-react"

import { CLUBS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount } from "@/lib/formatters"

export interface MissedSavingsEntry {
  transaction_id?: string
  store_name?: string
  amount?: number
  mcc_description?: string
  missed_store_discont?: Array<{
    club_id?: string
    missed_store?: Array<{ store_name?: string }>
  }>
}

interface MissedSavingsListProps {
  items: MissedSavingsEntry[]
  compact?: boolean
  limit?: number
}

function resolveClubName(clubId: string): string {
  return CLUBS.find((c) => c.id === clubId)?.name ?? clubId
}

export function MissedSavingsList({ items, compact = false, limit = 5 }: MissedSavingsListProps) {
  const relevant = items.filter((i) => (i.missed_store_discont?.length ?? 0) > 0).slice(0, limit)

  if (relevant.length === 0) {
    return (
      <p className={compact ? "text-xs text-slate-500" : "fintech-card-inset text-sm text-slate-600"}>
        {compact
          ? "No missed savings found in this analysis."
          : "No missed savings data yet. Once your spending is analyzed, we'll show you where you could have saved."}
      </p>
    )
  }

  if (compact) {
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

  return (
    <>
      {relevant.map((item, idx) => {
        const topDiscount = item.missed_store_discont?.[0]
        const clubName = topDiscount?.club_id ? resolveClubName(topDiscount.club_id) : null
        const altStoreNames = topDiscount?.missed_store?.slice(0, 3).map((s) => s.store_name).join(", ")
        const extraClubs = (item.missed_store_discont?.length ?? 0) - 1

        return (
          <div
            key={item.transaction_id ?? idx}
            className="space-y-2 rounded-2xl border border-slate-100 bg-slate-50/60 p-4"
          >
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
                <Store className="size-3.5" />
              </div>
              <p className="text-sm font-medium text-slate-800">
                You spent {formatAmount(item.amount)} at {item.store_name ?? "Unknown"}
              </p>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-lg bg-red-100 text-red-500">
                <TrendingDown className="size-3.5" />
              </div>
              <p className="text-sm text-slate-600">
                Savings were available in{" "}
                <span className="font-medium text-slate-700">{item.mcc_description ?? "this category"}</span>
              </p>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
                <Lightbulb className="size-3.5" />
              </div>
              <div className="min-w-0 text-sm text-slate-600">
                <p>
                  <span className="font-medium text-slate-700">{clubName}</span> had deals at {altStoreNames}
                </p>
                {extraClubs > 0 ? (
                  <p className={`${fintech.sectionEyebrow} mt-0.5`}>
                    +{extraClubs} more club{extraClubs !== 1 ? "s" : ""} with deals
                  </p>
                ) : null}
              </div>
            </div>
          </div>
        )
      })}
    </>
  )
}
