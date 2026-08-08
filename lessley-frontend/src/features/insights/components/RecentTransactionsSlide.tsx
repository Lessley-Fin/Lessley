import { useTranslation } from "react-i18next"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { INSIGHTS_DEFAULTS, formatCategoryLabel } from "@/lib/constants"
import { formatAmount, formatDate } from "@/lib/formatters"
import type { PersonalizationTransaction } from "@/lib/types"

interface RecentTransactionsSlideProps {
  transactions: PersonalizationTransaction[]
}

export function RecentTransactionsSlide({ transactions }: RecentTransactionsSlideProps) {
  const { t } = useTranslation()
  const recent = transactions.slice(0, INSIGHTS_DEFAULTS.CAROUSEL_LIST_LIMIT)

  if (recent.length === 0) {
    return (
      <CarouselSlideCard title={t("insights.recentTransactionsSlide.title")} subtitle={t("insights.recentTransactionsSlide.subtitle")}>
        <p className="text-sm text-muted-foreground">{t("insights.recentTransactionsSlide.empty")}</p>
      </CarouselSlideCard>
    )
  }

  return (
    <CarouselSlideCard title={t("insights.recentTransactionsSlide.title")} subtitle={t("insights.recentTransactionsSlide.subtitle")}>
      <ul className="no-scrollbar max-h-52 space-y-2 overflow-y-auto pe-1">
        {recent.map((tx, i) => {
          const description =
            tx.merchantName || tx.description?.description || tx.description?.fixedText || t("insights.recentTransactionsSlide.transaction")
          const amount = tx.amount?.chargedAmount?.amount ?? tx.amount?.originalAmount?.amount
          const date = tx.date?.transactionDate || tx.date?.bookingDate || tx.date?.valueDate || tx.createdAt || ""
          const category = tx.category?.main
            ? t(`categories.${tx.category.main}`, { defaultValue: formatCategoryLabel(tx.category.main) })
            : ""
          return (
            <li key={tx.id ?? `${description}-${date}-${i}`} className="flex items-center gap-3 rounded-2xl bg-secondary p-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{description}</p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(date)}
                  {category ? ` · ${category}` : ""}
                </p>
              </div>
              <span className="text-sm font-bold">−{formatAmount(amount)}</span>
            </li>
          )
        })}
      </ul>
    </CarouselSlideCard>
  )
}
