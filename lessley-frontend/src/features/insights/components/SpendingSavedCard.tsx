import { PiggyBank } from "lucide-react"

import { BarRow } from "@/components/shared/BarRow"
import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { Card, CardContent } from "@/components/ui/card"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount } from "@/lib/formatters"
import type { SpendingSavedByAccountInsight, SpendingSavedInsight } from "@/lib/types"

interface SpendingSavedCardProps {
  totalSaved: SpendingSavedInsight | null
  savedByAccount: SpendingSavedByAccountInsight[]
}

export function SpendingSavedCard({ totalSaved, savedByAccount }: SpendingSavedCardProps) {
  if (!totalSaved && savedByAccount.length === 0) return null

  const maxValue = Math.max(...savedByAccount.map((item) => item.total_saved), 0)

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={PiggyBank}
        iconColor="emerald"
        title="Spending saved"
        subtitle="Difference between charged and original amounts"
      />
      <CardContent className="space-y-3 px-5 pb-5 pt-0">
        <div className={fintech.metricEmerald}>
          <p className={fintech.metricLabel}>Total saved</p>
          <p className={fintech.metricValue}>{formatAmount(totalSaved?.total_saved)}</p>
        </div>
        {savedByAccount.length ? (
          <div className="space-y-2">
            <p className={fintech.sectionEyebrow}>By account</p>
            {savedByAccount.map((item) => (
              <BarRow
                key={item.accountId}
                label={item.accountNumber ?? item.accountId}
                value={item.total_saved}
                maxValue={maxValue}
                colorClassName="bg-emerald-500"
              />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
