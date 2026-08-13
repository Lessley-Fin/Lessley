import { useEffect, useMemo, useState } from "react"
import { Store } from "lucide-react"
import { useTranslation } from "react-i18next"

import { InfoDialog } from "@/components/shared/InfoDialog"
import { Carousel, CarouselContent, CarouselItem, type CarouselApi } from "@/components/ui/carousel"
import { AnalysisPeriodCard } from "@/features/insights/components/AnalysisPeriodCard"
import { emojiForStore } from "@/lib/constants"
import { formatAmount } from "@/lib/formatters"
import { getDirection } from "@/lib/i18n/config"
import type { MissedShop, StoreMatchBand } from "@/lib/types"
import { cn } from "@/lib/utils"

/**
 * Shops running a deal the user's own spending could have covered.
 *
 * One tab per confidence band, because the three do not mean the same thing and must not be
 * read as though they did. An EXACT or STRONG shop is the one the user walked into, so "you
 * missed a coupon here" is simply true. A SIMILAR shop only shares a word naming a line of
 * business — 'קפה ברלין' against 'קפה קפה' — so it is somewhere *like* theirs, and saying
 * they shopped there would be false. Separating them is what stops the weaker claim
 * borrowing the stronger one's credibility.
 */

const BANDS: StoreMatchBand[] = ["EXACT", "SIMILAR", "STRONG"]

const BAND_TONE: Record<StoreMatchBand, string> = {
  EXACT: "bg-emerald-500/12 text-emerald-600 dark:text-emerald-400",
  STRONG: "bg-sky-500/12 text-sky-600 dark:text-sky-400",
  SIMILAR: "bg-amber-500/12 text-amber-600 dark:text-amber-500",
}

interface MissedShopsSlideProps {
  shops: MissedShop[]
  isLoading: boolean
  days: number
  onDaysChange: (days: number) => void
}

export function MissedShopsSlide({ shops, isLoading, days, onDaysChange }: MissedShopsSlideProps) {
  const { t, i18n } = useTranslation()
  const direction = getDirection(i18n.language)
  const [chosenBand, setBand] = useState<StoreMatchBand>("EXACT")
  const [api, setApi] = useState<CarouselApi>()
  const [selected, setSelected] = useState(0)

  const byBand = useMemo(() => {
    const grouped = {} as Record<StoreMatchBand, MissedShop[]>
    for (const key of BANDS) grouped[key] = shops.filter((shop) => shop.match_band === key)
    return grouped
  }, [shops])

  // Fall through to a band that actually has something, so changing the period never leaves
  // the user staring at an empty tab. Derived rather than corrected after the fact — the
  // chosen band is remembered, and returns as soon as it has shops again.
  const band = byBand[chosenBand].length > 0 ? chosenBand : (BANDS.find((key) => byBand[key].length > 0) ?? chosenBand)
  const visible = byBand[band]

  useEffect(() => {
    if (!api) return
    const onSelect = () => setSelected(api.selectedScrollSnap())
    onSelect()
    api.on("select", onSelect)
    return () => {
      api.off("select", onSelect)
    }
  }, [api])

  useEffect(() => {
    api?.scrollTo(0)
  }, [band, api])

  return (
    <div className="flex h-[420px] flex-col gap-2.5 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-3">
        <span className="flex size-10 items-center justify-center rounded-full bg-accent">
          <Store className="size-4 text-accent-foreground" aria-hidden />
        </span>
        <div className="flex-1">
          <p className="font-bold">{t("recommendations.missedShopsSlide.title")}</p>
          <p className="text-xs text-muted-foreground">
            {t("recommendations.missedShopsSlide.subtitle", { count: shops.length })}
          </p>
        </div>
        <InfoDialog
          ariaLabel={t("recommendations.missedShopsSlide.infoDialog.ariaLabel")}
          title={t("recommendations.missedShopsSlide.infoDialog.title")}
        >
          <p className="text-sm text-muted-foreground">{t("recommendations.missedShopsSlide.infoDialog.body")}</p>
        </InfoDialog>
      </div>

      <AnalysisPeriodCard value={days} onChange={onDaysChange} />

      <div className="flex gap-1 rounded-full bg-secondary p-1">
        {BANDS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setBand(key)}
            disabled={byBand[key].length === 0}
            className={cn(
              "flex-1 rounded-full px-2 py-1.5 text-xs font-semibold transition-colors disabled:opacity-40",
              band === key ? BAND_TONE[key] : "text-muted-foreground",
            )}
          >
            {t(`recommendations.missedShopsSlide.band.${key}.label`)}
            {byBand[key].length > 0 && ` · ${byBand[key].length}`}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">{t("recommendations.missedShopsSlide.loading")}</p>
      ) : visible.length === 0 ? (
        <p className="rounded-2xl bg-secondary p-4 text-sm text-muted-foreground">
          {t("recommendations.missedShopsSlide.empty")}
        </p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <p className="text-xs text-muted-foreground">{t(`recommendations.missedShopsSlide.band.${band}.hint`)}</p>

          <Carousel setApi={setApi} opts={{ align: "start", direction }} className="min-h-0 flex-1">
            <CarouselContent className="h-full">
              {visible.map((shop) => (
                <CarouselItem key={shop.store_id} className="h-full">
                  <ShopCard shop={shop} />
                </CarouselItem>
              ))}
            </CarouselContent>
          </Carousel>

          {visible.length > 1 && (
            <div className="flex items-center justify-center gap-3">
              <CarouselPreviousStandalone api={api} label={t("common.previousSlide")} />
              <span className="text-xs font-semibold tabular-nums text-muted-foreground">
                {selected + 1} / {visible.length}
              </span>
              <CarouselNextStandalone api={api} label={t("common.nextSlide")} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * The shipped CarouselPrevious/Next read their carousel from context, which is only available
 * inside <Carousel>. The arrows sit below it here, so they drive the api directly.
 */
function CarouselPreviousStandalone({ api, label }: { api: CarouselApi | undefined; label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => api?.scrollPrev()}
      disabled={!api?.canScrollPrev()}
      className="flex size-7 items-center justify-center rounded-full border border-border bg-card text-sm disabled:opacity-40"
    >
      ‹
    </button>
  )
}

function CarouselNextStandalone({ api, label }: { api: CarouselApi | undefined; label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => api?.scrollNext()}
      disabled={!api?.canScrollNext()}
      className="flex size-7 items-center justify-center rounded-full border border-border bg-card text-sm disabled:opacity-40"
    >
      ›
    </button>
  )
}

function ShopCard({ shop }: { shop: MissedShop }) {
  const { t } = useTranslation()
  const topDeal = shop.deal_titles[0]

  return (
    <div className="flex h-full flex-col gap-2 rounded-2xl bg-secondary p-3">
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-card text-base">
          {emojiForStore(shop.store_name)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">{shop.store_name}</p>
          <p className="text-xs text-muted-foreground">
            {t("recommendations.missedShopsSlide.dealCount", { count: shop.deal_count })}
            {shop.also_known_as.length > 0 && ` · ${shop.also_known_as[0]}`}
          </p>
        </div>
        <span className="shrink-0 text-sm font-bold">{formatAmount(shop.covered_amount)}</span>
      </div>

      {topDeal && <p className="line-clamp-2 text-xs text-muted-foreground">{topDeal}</p>}

      <p className="text-xs font-semibold">
        {shop.is_same_store
          ? t("recommendations.missedShopsSlide.coversHere", { count: shop.covered_transaction_count })
          : t("recommendations.missedShopsSlide.coversSimilar", { count: shop.covered_transaction_count })}
      </p>

      <ul className="no-scrollbar min-h-0 flex-1 space-y-0.5 overflow-y-auto">
        {shop.purchases.map((purchase) => (
          <li
            key={purchase.transaction_id}
            className="flex items-center justify-between gap-2 text-xs text-muted-foreground"
          >
            <span className="truncate">{purchase.merchant_name}</span>
            <span className="shrink-0">{formatAmount(purchase.amount)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
