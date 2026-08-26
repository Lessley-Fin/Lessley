import { PiggyBank, CreditCard } from "lucide-react"
import { useTranslation } from "react-i18next"

import { InfoDialog } from "@/components/shared/InfoDialog"
import { AnalysisPeriodCard } from "@/features/insights/components/AnalysisPeriodCard"
import { useAccounts } from "@/features/insights/hooks"
import { emojiForStore } from "@/lib/constants"
import { formatAmount } from "@/lib/formatters"
import type { AppliedSavings } from "@/lib/types"

/**
 * Money the user did *not* pay, because they put a club's own card on the counter.
 *
 * The mirror of {@link MissedShopsSlide}, off the same payload: that one leads with the
 * purchases that missed a deal, this one with the purchases that took it. A נטען card is
 * loaded up front and only spends at the club's partner shops, so a purchase charged to one
 * already carried the discount — telling the user they missed out on it was the bug this tab
 * exists to correct.
 *
 * No confidence bands and no carousel. Both belong to the missed slide, where the question is
 * "is this really your shop, and is the suggestion worth acting on". Neither applies to a
 * receipt: the card either paid or it did not, and there is nothing to act on.
 *
 * **Nothing is computed here.** Totals and counts arrive final — see the note on
 * {@link MissedShopsSlide} for why no client re-derives them.
 *
 * One thing this screen must never say: *which* club paid. The evidence is a settled row the
 * card was never billed for, which says no money left the account and nothing at all about
 * whose card it was. `club_ids` on these merchants is empty for that reason.
 */

interface AppliedDiscountsSlideProps {
  applied: AppliedSavings
  isLoading: boolean
  days: number
  onDaysChange: (days: number) => void
}

export function AppliedDiscountsSlide({ applied, isLoading, days, onDaysChange }: AppliedDiscountsSlideProps) {
  const { t } = useTranslation()

  // Resolved on the client so the endpoint stays a set of ids. Naming is not arithmetic.
  const { data: accounts = [] } = useAccounts()
  const accountNames = new Map(
    accounts.map((account) => [account.id, [account.product, account.providerId].filter(Boolean).join(" · ") || account.id]),
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span className="flex size-10 items-center justify-center rounded-full bg-emerald-500/12">
            <PiggyBank className="size-4 text-emerald-600 dark:text-emerald-400" aria-hidden />
          </span>
          <div className="flex-1">
            <p className="font-bold">{t("recommendations.appliedDiscountsSlide.title")}</p>
            <p className="text-xs text-muted-foreground">
              {t("recommendations.appliedDiscountsSlide.subtitle", {
                count: applied.purchase_count,
                amount: formatAmount(applied.total_amount),
              })}
            </p>
          </div>
          <InfoDialog
            ariaLabel={t("recommendations.appliedDiscountsSlide.infoDialog.ariaLabel")}
            title={t("recommendations.appliedDiscountsSlide.infoDialog.title")}
          >
            <div className="flex flex-col gap-3 text-sm text-muted-foreground">
              <p>{t("recommendations.appliedDiscountsSlide.infoDialog.intro")}</p>
              <p>{t("recommendations.appliedDiscountsSlide.infoDialog.howWeKnow")}</p>
            </div>
          </InfoDialog>
        </div>

        <AnalysisPeriodCard value={days} onChange={onDaysChange} />
      </div>

      {isLoading ? (
        <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground shadow-[var(--shadow-card)]">
          {t("recommendations.appliedDiscountsSlide.loading")}
        </p>
      ) : applied.merchants.length === 0 ? (
        <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground shadow-[var(--shadow-card)]">
          {t("recommendations.appliedDiscountsSlide.empty")}
        </p>
      ) : (
        <div className="flex flex-col gap-2 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
          <p className="text-xs text-muted-foreground">{t("recommendations.appliedDiscountsSlide.hint")}</p>

          <ul className="space-y-1.5">
            {applied.merchants.map((merchant) => {
              // The card, not the club: it is the only part of this we can actually name.
              const cards = merchant.account_ids.map((id) => accountNames.get(id) ?? id)

              return (
                <li key={merchant.merchant_name} className="flex items-start gap-2 rounded-2xl bg-secondary px-3 py-2.5">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-card text-sm">
                    {emojiForStore(merchant.merchant_name)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{merchant.merchant_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {t("recommendations.appliedDiscountsSlide.purchaseCount", {
                        count: merchant.purchase_count,
                      })}
                    </p>
                    {cards.length > 0 && (
                      <p className="mt-0.5 flex items-start gap-1 text-[11px] text-emerald-600 dark:text-emerald-400">
                        <CreditCard className="mt-px size-3 shrink-0" aria-hidden />
                        <span className="min-w-0 break-words">
                          {t("recommendations.appliedDiscountsSlide.paidWith", { sources: cards.join(", ") })}
                        </span>
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-0.5">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                      {t("recommendations.appliedDiscountsSlide.spentLabel")}
                    </p>
                    <span className="rounded-full bg-card px-2.5 py-1 text-sm font-bold">
                      {formatAmount(merchant.amount)}
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
