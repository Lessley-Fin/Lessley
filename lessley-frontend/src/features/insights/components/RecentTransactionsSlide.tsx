import { useTranslation } from "react-i18next"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { INSIGHTS_DEFAULTS, formatCategoryLabel } from "@/lib/constants"
import { formatAmount, formatDate } from "@/lib/formatters"
import type { PersonalizationTransaction } from "@/lib/types"
import { cn } from "@/lib/utils"

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
          const charged = tx.amount?.chargedAmount?.amount
          const amount = charged ?? tx.amount?.originalAmount?.amount
          // The feed signs its amounts: a purchase is negative, a refund or credit positive.
          // formatAmount renders that sign itself, so the magnitude goes in and the sign is
          // shown once, here — prefixing the signed value printed every purchase as "−-₪86.00".
          const isRefund = typeof amount === "number" && amount > 0
          // A settled row the card was never billed for: a voucher, gift card or waived fee.
          // It is still a purchase and still belongs in the list, but nothing was deducted, so
          // it must not carry a minus. Mirrors TransactionAmountService.was_never_charged.
          const wasNeverCharged =
            tx.status === "BOOKED" && (charged === null || charged === undefined || charged === 0) && !isRefund
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
              <span
                className={cn(
                  "text-sm font-bold",
                  isRefund && "text-emerald-600",
                  wasNeverCharged && "text-muted-foreground",
                )}
              >
                {typeof amount !== "number"
                  ? formatAmount(amount)
                  : `${wasNeverCharged ? "" : isRefund ? "+" : "−"}${formatAmount(Math.abs(amount))}`}
              </span>
            </li>
          )
        })}
      </ul>
    </CarouselSlideCard>
  )
}
