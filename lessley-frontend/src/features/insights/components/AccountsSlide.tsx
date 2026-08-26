import { useMemo } from "react"
import { CreditCard } from "lucide-react"
import { useTranslation } from "react-i18next"

import { CarouselSlideCard } from "@/components/shared/CarouselSlideCard"
import { useAccounts } from "@/features/insights/hooks"
import { INSIGHTS_DEFAULTS } from "@/lib/constants"
import { formatAmount, maskAccountNumber } from "@/lib/formatters"
import type { TopAccountInsight } from "@/lib/types"

interface AccountsSlideProps {
  accounts: TopAccountInsight[]
}

export function AccountsSlide({ accounts }: AccountsSlideProps) {
  const { t } = useTranslation()
  const list = accounts.slice(0, INSIGHTS_DEFAULTS.CAROUSEL_LIST_LIMIT)

  // The top-accounts insight only names an account by id — resolve it against the accounts
  // list (already fetched elsewhere in the app) to show the bank/product label, the same
  // pattern MissedShopsSlide uses.
  const { data: openFinanceAccounts = [] } = useAccounts()
  const accountsById = useMemo(
    () => new Map(openFinanceAccounts.map((account) => [account.id, account])),
    [openFinanceAccounts],
  )

  if (list.length === 0) {
    return (
      <CarouselSlideCard title={t("insights.accountsSlide.title")} subtitle={t("insights.accountsSlide.subtitle")}>
        <p className="text-sm text-muted-foreground">{t("insights.accountsSlide.empty")}</p>
        <p className="px-1 pt-1 text-[11px] leading-relaxed text-muted-foreground">
        {t("insights.explain.sourceBlind")}
      </p>
    </CarouselSlideCard>
    )
  }

  return (
    <CarouselSlideCard title={t("insights.accountsSlide.title")} subtitle={t("insights.accountsSlide.subtitle")}>
      <ul className="no-scrollbar max-h-52 space-y-2 overflow-y-auto pe-1">
        {list.map((account) => {
          const match = accountsById.get(account.accountId)
          const label = [match?.product, match?.providerId].filter(Boolean).join(" · ")

          return (
            <li key={account.accountId} className="flex items-center gap-3 rounded-2xl bg-secondary p-3">
              <CreditCard className="size-4 text-primary" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">
                  {account.accountNumber ? maskAccountNumber(account.accountNumber) : account.accountId}
                </p>
                {label ? <p className="truncate text-xs text-muted-foreground">{label}</p> : null}
                <p className="text-xs text-muted-foreground">
                  {t("insights.common.transactionsCount", { count: account.total_count })}
                </p>
              </div>
              <span className="text-sm font-bold">{formatAmount(account.total_amount)}</span>
            </li>
          )
        })}
      </ul>
    </CarouselSlideCard>
  )
}
