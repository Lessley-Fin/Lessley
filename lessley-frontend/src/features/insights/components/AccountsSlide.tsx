import { CreditCard } from "lucide-react"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { formatAmount, maskAccountNumber } from "@/lib/formatters"
import type { TopAccountInsight } from "@/lib/types"

interface AccountsSlideProps {
  accounts: TopAccountInsight[]
}

export function AccountsSlide({ accounts }: AccountsSlideProps) {
  const list = accounts.slice(0, INSIGHTS_DEFAULTS.CAROUSEL_LIST_LIMIT)

  if (list.length === 0) {
    return (
      <CarouselSlideCard title="Spending by accounts" subtitle="Open Banking connected">
        <p className="text-sm text-muted-foreground">No linked accounts with activity yet.</p>
      </CarouselSlideCard>
    )
  }

  return (
    <CarouselSlideCard title="Spending by accounts" subtitle="Open Banking connected">
      <ul className="no-scrollbar max-h-52 space-y-2 overflow-y-auto pr-1">
        {list.map((account) => (
          <li key={account.accountId} className="flex items-center gap-3 rounded-2xl bg-secondary p-3">
            <CreditCard className="size-4 text-primary" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">
                {account.accountNumber ? maskAccountNumber(account.accountNumber) : account.accountId}
              </p>
              <p className="text-xs text-muted-foreground">{account.total_count} transactions</p>
            </div>
            <span className="text-sm font-bold">{formatAmount(account.total_amount)}</span>
          </li>
        ))}
      </ul>
    </CarouselSlideCard>
  )
}
