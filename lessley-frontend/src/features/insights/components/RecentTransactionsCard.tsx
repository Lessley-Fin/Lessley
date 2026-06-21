import { ListRow } from "@/components/shared/ListRow"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount, formatDate } from "@/lib/formatters"
import type { PersonalizationTransaction } from "@/lib/types"

interface RecentTransactionsCardProps {
  transactions: PersonalizationTransaction[]
  isLoading: boolean
}

export function RecentTransactionsCard({ transactions, isLoading }: RecentTransactionsCardProps) {
  return (
    <Card className="fintech-card border-0">
      <CardHeader className="px-5 pb-2 pt-5">
        <CardTitle className={fintech.sectionTitle}>Recent transactions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 px-5 pb-5 pt-0 text-sm">
        {isLoading ? <p className="text-slate-500">Loading transactions...</p> : null}
        {!isLoading && transactions.length === 0 ? (
          <p className="text-slate-500">No transactions found.</p>
        ) : null}
        {transactions.slice(0, INSIGHTS_DEFAULTS.RECENT_TRANSACTIONS_LIMIT).map((tx) => {
          const description =
            tx.merchantName ||
            tx.description?.description ||
            tx.description?.fixedText ||
            tx.description?.initialClean ||
            "Transaction"
          const amount = tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount
          const currency = tx.amount?.chargedAmount?.currency ?? tx.amount?.originalAmount?.currency ?? ""
          const date =
            tx.date?.transactionDate || tx.date?.bookingDate || tx.date?.valueDate || tx.createdAt || ""
          return (
            <ListRow key={tx.id ?? `${description}-${date}`}>
              <div className="min-w-0">
                <p className="font-medium text-slate-800">{description}</p>
                <p className="text-xs text-slate-500">{formatDate(date)}</p>
              </div>
              <p className={`${fintech.amount} shrink-0 text-sm`}>
                {formatAmount(amount, currency)}
              </p>
            </ListRow>
          )
        })}
      </CardContent>
    </Card>
  )
}
