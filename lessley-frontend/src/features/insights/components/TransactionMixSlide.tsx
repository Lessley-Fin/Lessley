import { useTranslation } from "react-i18next"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { formatAmount } from "@/lib/formatters"
import type { TransactionMixEntry } from "@/lib/types"
import { cn } from "@/lib/utils"

// One colour per kind, held apart from the category palette so the bar reads as a fixed legend
// rather than as data. Everyday spending is deliberately the quietest of the five: it is the
// bulk of the bar, and the exceptions are what the slide exists to explain.
const KIND_STYLE: Record<TransactionMixEntry["kind"], { bar: string; dot: string }> = {
  ordinary: { bar: "bg-primary/25", dot: "bg-primary/25" },
  foreign: { bar: "bg-primary", dot: "bg-primary" },
  installment: { bar: "bg-navy", dot: "bg-navy" },
  refund: { bar: "bg-emerald-500", dot: "bg-emerald-500" },
  voucher: { bar: "bg-amber-500", dot: "bg-amber-500" },
}

interface TransactionMixSlideProps {
  composition: TransactionMixEntry[]
  periodLabel: string
}

export function TransactionMixSlide({ composition, periodLabel }: TransactionMixSlideProps) {
  const { t } = useTranslation()
  const title = t("insights.transactionMixSlide.title")
  const subtitle = t("insights.transactionMixSlide.subtitle", { period: periodLabel })

  const total = composition.reduce((sum, entry) => sum + entry.count, 0)

  if (total === 0) {
    return (
      <CarouselSlideCard title={title} subtitle={subtitle}>
        <p className="text-sm text-muted-foreground">{t("insights.transactionMixSlide.empty")}</p>
      </CarouselSlideCard>
    )
  }

  return (
    <CarouselSlideCard title={title} subtitle={subtitle}>
      {/* The bar is proportional to counts, not money: this answers "how often", and the
          amount beside each row answers "how much". A single voucher worth ₪176 should not
          out-measure twenty everyday purchases. */}
      <div
        className="flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full"
        role="img"
        aria-label={composition
          .map((entry) => `${t(`insights.transactionKinds.${entry.kind}.label`)}: ${entry.count}`)
          .join(", ")}
      >
        {composition.map((entry) => (
          <div
            key={entry.kind}
            className={cn("h-full rounded-full", KIND_STYLE[entry.kind].bar)}
            // A kind with a single transaction still has to be visible, so every segment keeps
            // a floor of 2% regardless of how small its true share is.
            style={{ width: `${Math.max((entry.count / total) * 100, 2)}%` }}
          />
        ))}
      </div>

      <ul className="no-scrollbar mt-4 max-h-52 space-y-2 overflow-y-auto pe-1">
        {composition.map((entry) => (
          <li key={entry.kind} className="flex items-start gap-3 rounded-2xl bg-secondary p-3">
            <span
              className={cn("mt-1.5 size-2.5 shrink-0 rounded-full", KIND_STYLE[entry.kind].dot)}
              aria-hidden
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{t(`insights.transactionKinds.${entry.kind}.label`)}</p>
              <p className="text-xs text-muted-foreground">
                {t(`insights.transactionKinds.${entry.kind}.note`)}
              </p>
              <MixDetail entry={entry} />
            </div>
            <div className="shrink-0 text-end">
              <p className="text-sm font-bold">{formatAmount(entry.amount)}</p>
              <p className="text-xs text-muted-foreground">
                {t("insights.transactionMixSlide.count", { count: entry.count })}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </CarouselSlideCard>
  )
}

/** The extra line two kinds earn: what the conversions cost, and how many plans are running. */
function MixDetail({ entry }: { entry: TransactionMixEntry }) {
  const { t } = useTranslation()

  if (entry.kind === "foreign" && entry.markup_fees) {
    return (
      <p className="mt-0.5 text-xs font-medium text-primary">
        {t("insights.transactionMixSlide.markupFees", { amount: formatAmount(entry.markup_fees) })}
      </p>
    )
  }

  if (entry.kind === "installment" && entry.plan_count) {
    return (
      <p className="mt-0.5 text-xs font-medium text-primary">
        {t("insights.transactionMixSlide.plans", { count: entry.plan_count })}
      </p>
    )
  }

  if (entry.kind === "voucher") {
    return (
      <p className="mt-0.5 text-xs font-medium text-amber-600">
        {t("insights.transactionMixSlide.savedNote")}
      </p>
    )
  }

  return null
}
