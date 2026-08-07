import { Receipt, Wallet } from "lucide-react"

import { formatAmount } from "@/lib/formatters"

interface StatsGridCardProps {
  transactionCount: number
  totalAmount: number
  periodLabel: string
}

export function StatsGridCard({ transactionCount, totalAmount, periodLabel }: StatsGridCardProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]">
        <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          <Receipt className="size-3.5" aria-hidden />
          Transactions
        </div>
        <p className="mt-2 text-xl font-bold">{transactionCount}</p>
        <p className="text-xs text-muted-foreground">{periodLabel}</p>
      </div>
      <div className="rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]">
        <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          <Wallet className="size-3.5" aria-hidden />
          Total amount
        </div>
        <p className="mt-2 text-xl font-bold">{formatAmount(totalAmount)}</p>
        <p className="text-xs text-muted-foreground">All linked cards</p>
      </div>
    </div>
  )
}
