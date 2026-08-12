import { useState } from "react"
import { ChevronDown, RefreshCw, TrendingDown } from "lucide-react"
import { useTranslation } from "react-i18next"

import { InfoDialog } from "@/components/shared/InfoDialog"
import { Button } from "@/components/ui/button"
import { formatAmount } from "@/lib/formatters"
import type { ClubDto, TransactionInsight } from "@/lib/types"
import { cn, getClubName } from "@/lib/utils"

interface MissedSavingsSlideProps {
  insights: TransactionInsight[]
  clubs: ClubDto[]
  onRecalculate: () => void
  isPending: boolean
}

export function MissedSavingsSlide({ insights, clubs, onRecalculate, isPending }: MissedSavingsSlideProps) {
  const { t } = useTranslation()
  const [openId, setOpenId] = useState<string | null>(null)
  const items = insights.filter((i) => (i.missed_store_discont?.length ?? 0) > 0).slice(0, 10)

  return (
    <div className="flex h-[420px] flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-3">
        <span className="flex size-10 items-center justify-center rounded-full bg-accent">
          <TrendingDown className="size-4 text-accent-foreground" aria-hidden />
        </span>
        <div className="flex-1">
          <p className="font-bold">{t("recommendations.missedSavingsSlide.title")}</p>
          <p className="text-xs text-muted-foreground">{t("recommendations.missedSavingsSlide.subtitle")}</p>
        </div>
        <InfoDialog
          ariaLabel={t("recommendations.missedSavingsSlide.infoDialog.ariaLabel")}
          title={t("recommendations.missedSavingsSlide.infoDialog.title")}
        >
          <p className="text-sm text-muted-foreground">{t("recommendations.missedSavingsSlide.infoDialog.body")}</p>
        </InfoDialog>
        <Button
          type="button"
          variant="pill"
          size="icon"
          aria-label={t("recommendations.missedSavingsSlide.recalculateAria")}
          onClick={onRecalculate}
          disabled={isPending}
        >
          <RefreshCw className={isPending ? "animate-spin" : ""} aria-hidden />
        </Button>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("recommendations.missedSavingsSlide.empty")}</p>
      ) : (
        <ul className="no-scrollbar min-h-0 flex-1 space-y-2 overflow-y-auto pe-1">
          {items.map((item) => {
            const isOpen = openId === item.transaction_id
            return (
              <li key={item.transaction_id} className="rounded-2xl bg-secondary p-3">
                <button
                  type="button"
                  onClick={() => setOpenId(isOpen ? null : item.transaction_id)}
                  className="flex w-full items-center gap-3 text-start"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{item.store_name}</p>
                    <p className="text-xs text-muted-foreground">{item.mcc_code}</p>
                  </div>
                  <span className="text-sm font-bold">{formatAmount(item.amount)}</span>
                  <ChevronDown className={cn("size-4 shrink-0 transition-transform", isOpen && "rotate-180")} aria-hidden />
                </button>
                {isOpen ? (
                  <div className="mt-3 space-y-2 border-t border-border pt-3">
                    <p className="text-xs text-muted-foreground">{item.mcc_description}</p>
                    {item.missed_store_discont.map((discount) => (
                      <div key={discount.club_id} className="rounded-xl bg-card p-3">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-bold">{getClubName(clubs, discount.club_id)}</p>
                          <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold text-secondary-foreground">
                            {t("recommendations.missedSavingsSlide.storesCount", { count: discount.store_count })}
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {discount.missed_store.map((store) => (
                            <span
                              key={store.store_id}
                              className="rounded-full bg-accent px-2.5 py-1 text-[11px] font-medium text-accent-foreground"
                            >
                              {store.store_name}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
