import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { emojiForStore } from "@/lib/constants"
import { formatAmount } from "@/lib/formatters"
import type { PersonalizationTransaction } from "@/lib/types"

interface TrueCostSlideProps {
  transactions: PersonalizationTransaction[]
  periodDays: number
}

function txAmount(tx: PersonalizationTransaction): number {
  return tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount ?? 0
}

export function TrueCostSlide({ transactions, periodDays }: TrueCostSlideProps) {
  const groups = new Map<string, { count: number; total: number }>()
  for (const tx of transactions) {
    const name = tx.merchantName?.trim()
    if (!name) continue
    const entry = groups.get(name) ?? { count: 0, total: 0 }
    entry.count += 1
    entry.total += txAmount(tx)
    groups.set(name, entry)
  }

  const recurring = [...groups.entries()]
    .filter(([, v]) => v.count >= 2)
    .sort((a, b) => b[1].count - a[1].count)[0]

  if (!recurring) {
    return (
      <CarouselSlideCard title="True cost" subtitle="The habit behind the number">
        <p className="text-sm text-muted-foreground">Not enough repeat purchases yet to spot a recurring habit.</p>
      </CarouselSlideCard>
    )
  }

  const [name, { count, total }] = recurring
  const visitsPerWeek = count / (periodDays / 7)
  const avgPerVisit = total / count
  const perWeek = avgPerVisit * visitsPerWeek
  const perYear = perWeek * 52
  const fewerVisits = Math.max(1, Math.min(count - 1, Math.round(visitsPerWeek * 0.25)))
  const yearlyKept = avgPerVisit * fewerVisits * 52

  return (
    <CarouselSlideCard title="True cost" subtitle="The habit behind the number">
      <div className="rounded-2xl bg-secondary p-4">
        <p className="text-3xl">{emojiForStore(name)}</p>
        <p className="mt-2 font-semibold">{name}</p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-muted-foreground">Per week</p>
            <p className="text-lg font-bold">{formatAmount(perWeek)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Per year</p>
            <p className="text-lg font-bold text-primary">{formatAmount(perYear)}</p>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          {fewerVisits} fewer {fewerVisits === 1 ? "visit" : "visits"} a week could keep {formatAmount(yearlyKept)} a
          year.
        </p>
      </div>
    </CarouselSlideCard>
  )
}
