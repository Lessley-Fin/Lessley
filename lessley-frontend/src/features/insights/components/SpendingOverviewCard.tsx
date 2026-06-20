import { TrendingUp } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { ListRow } from "@/components/shared/ListRow"
import { Card, CardContent } from "@/components/ui/card"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { formatAmount } from "@/lib/formatters"
import type { PersonalizationTransaction, SpendingCategoryInsight } from "@/lib/types"

interface SpendingOverviewCardProps {
  transactions: PersonalizationTransaction[]
  categories: SpendingCategoryInsight[]
  isLoading: boolean
  error: string
}

export function SpendingOverviewCard({ transactions, categories, isLoading, error }: SpendingOverviewCardProps) {
  const topCategories = categories.slice(0, INSIGHTS_DEFAULTS.TOP_CATEGORIES_LIMIT)
  const moreHotCategories = categories.slice(
    INSIGHTS_DEFAULTS.MORE_CATEGORIES_OFFSET,
    INSIGHTS_DEFAULTS.MORE_CATEGORIES_LIMIT,
  )
  const topCategory = topCategories[0]

  const totalTransactionAmount = transactions.reduce((sum, tx) => {
    const amount = tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount
    return sum + (typeof amount === "number" ? amount : 0)
  }, 0)

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon icon={TrendingUp} iconColor="blue" title="Spending overview" />
      <CardContent className="space-y-3 px-5 pb-5 pt-0 text-sm">
        {isLoading ? <p className="text-slate-500">Loading insights...</p> : null}
        <ErrorAlert message={error} />
        {!isLoading && !error ? (
          <>
            <div className="grid grid-cols-2 gap-2.5">
              <div className={fintech.metricBlue}>
                <p className={fintech.metricLabel}>Transactions</p>
                <p className={fintech.metricValue}>{transactions.length}</p>
              </div>
              <div className={fintech.metricViolet}>
                <p className={fintech.metricLabel}>Total amount</p>
                <p className={fintech.metricValue}>{formatAmount(totalTransactionAmount)}</p>
              </div>
              <div className={fintech.metricAmber}>
                <p className={fintech.metricLabel}>Top category</p>
                <p className="mt-1 line-clamp-1 text-sm font-medium text-slate-800">
                  {topCategory?.category ?? "-"}
                </p>
                <p className="text-xs text-slate-500">
                  {topCategory ? `${topCategory.total_count} tx` : "No category data"}
                </p>
              </div>
              <div className={fintech.metricEmerald}>
                <p className={fintech.metricLabel}>Category spend</p>
                <p className={fintech.metricValue}>{formatAmount(topCategory?.total_amount)}</p>
              </div>
            </div>
            {moreHotCategories.length ? (
              <div className="space-y-2">
                <p className={fintech.sectionEyebrow}>Trending categories</p>
                {moreHotCategories.map((item) => (
                  <ListRow key={item.category}>
                    <p className="font-medium text-slate-700">{item.category}</p>
                    <p className={`${fintech.amount} text-sm`}>
                      {item.total_count} tx · {formatAmount(item.total_amount)}
                    </p>
                  </ListRow>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}
