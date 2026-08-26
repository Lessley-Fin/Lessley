import { Receipt, Wallet } from "lucide-react"
import { useTranslation } from "react-i18next"

import { formatAmount } from "@/lib/formatters"
import type { TransactionMixEntry } from "@/lib/types"

// Each kind's phrasing lives in the locale files. Everyday purchases are absent on purpose: the
// transaction count already implies them, so naming them again would add nothing.
const KIND_PHRASE: Partial<Record<TransactionMixEntry["kind"], string>> = {
  foreign: "abroad",
  installment: "installments",
  refund: "refunded",
  statement: "discounted",
  coupon: "coupons",
}

interface StatsGridCardProps {
  transactionCount: number
  totalAmount: number
  periodLabel: string
  composition?: TransactionMixEntry[]
}

export function StatsGridCard({
  transactionCount,
  totalAmount,
  periodLabel,
  composition = [],
}: StatsGridCardProps) {
  const { t } = useTranslation()

  const notable = composition.flatMap((entry) => {
    const phrase = KIND_PHRASE[entry.kind]
    if (!phrase || entry.count === 0) return []
    return [t(`insights.statsGrid.${phrase}`, { count: entry.count })]
  })

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            <Receipt className="size-3.5" aria-hidden />
            {t("insights.statsGrid.transactions")}
          </div>
          <p className="mt-2 text-xl font-bold">{transactionCount}</p>
          <p className="text-xs text-muted-foreground">{periodLabel}</p>
        </div>
        <div className="rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            <Wallet className="size-3.5" aria-hidden />
            {t("insights.statsGrid.totalAmount")}
          </div>
          <p className="mt-2 text-xl font-bold">{formatAmount(totalAmount)}</p>
          <p className="text-xs text-muted-foreground">{t("insights.statsGrid.allLinkedCards")}</p>
        </div>
      </div>
      {/* Inline, not behind an info button. A total that quietly leaves something out is worse
          than one that says so where it is read. */}
      <p className="px-1 text-[11px] leading-relaxed text-muted-foreground">
        {t("insights.explain.spendTotal")}
      </p>
      {notable.length > 0 && (
        <p className="px-1 text-xs text-muted-foreground">
          {notable.join(t("insights.statsGrid.breakdownSeparator"))}
        </p>
      )}
    </div>
  )
}
