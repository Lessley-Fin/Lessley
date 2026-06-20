import { Landmark } from "lucide-react"

import { ListRow } from "@/components/shared/ListRow"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount } from "@/lib/formatters"
import type { TopAccountInsight } from "@/lib/types"

interface ActiveAccountsCardProps {
  accounts: TopAccountInsight[]
}

export function ActiveAccountsCard({ accounts }: ActiveAccountsCardProps) {
  if (accounts.length === 0) return null

  return (
    <Card className="fintech-card border-0">
      <CardHeader className="flex-row items-center gap-2 space-y-0 px-5 pb-2 pt-5">
        <Landmark className="size-4 text-slate-500" />
        <CardTitle className={fintech.sectionTitle}>Most active accounts</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 px-5 pb-5 pt-0 text-sm">
        {accounts.map((item) => (
          <ListRow key={item.accountId}>
            <div>
              <p className="font-medium text-slate-800">{item.accountNumber ?? item.accountId}</p>
              <p className="text-xs text-slate-500">{item.total_count} transactions</p>
            </div>
            <p className={fintech.amount}>{formatAmount(item.total_amount)}</p>
          </ListRow>
        ))}
      </CardContent>
    </Card>
  )
}
