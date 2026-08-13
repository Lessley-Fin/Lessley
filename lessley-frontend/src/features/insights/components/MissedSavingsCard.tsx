import { useState } from "react"
import { useTranslation } from "react-i18next"

import { CarouselDots } from "@/components/shared/CarouselDots"
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel"
import { emojiForStore } from "@/lib/constants"
import { formatAmount } from "@/lib/formatters"
import { getDirection } from "@/lib/i18n/config"
import type { MissedShop, StoreMatchBand } from "@/lib/types"
import { cn } from "@/lib/utils"

/**
 * Shops running a deal the user could have used.
 *
 * Split into one carousel per confidence band, because the three do not mean the same thing
 * and must not be read as if they did. An EXACT or STRONG shop is the one the user walked
 * into — "you missed a coupon here" is simply true. A SIMILAR shop only shares a word naming
 * a line of business ('קפה ברלין' against 'קפה קפה'), so it is somewhere *like* theirs, and
 * saying they shopped there would be false. Keeping them in separate carousels is what stops
 * the weaker claim borrowing the stronger one's credibility.
 */

const BAND_ORDER: StoreMatchBand[] = ["EXACT", "SIMILAR", "STRONG"]

const BAND_TONE: Record<StoreMatchBand, string> = {
  EXACT: "bg-emerald-500/12 text-emerald-600 dark:text-emerald-400",
  STRONG: "bg-sky-500/12 text-sky-600 dark:text-sky-400",
  SIMILAR: "bg-amber-500/12 text-amber-600 dark:text-amber-500",
}

interface MissedSavingsCardProps {
  shops: MissedShop[]
}

export function MissedSavingsCard({ shops }: MissedSavingsCardProps) {
  const { t } = useTranslation()

  const byBand = BAND_ORDER.map((band) => ({
    band,
    shops: shops.filter((shop) => shop.match_band === band),
  })).filter((group) => group.shops.length > 0)

  return (
    <section className="space-y-4 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {t("insights.missedSavings.eyebrow")}
        </p>
        <h2 className="text-lg font-bold tracking-tight">{t("insights.missedSavings.title")}</h2>
        <p className="text-sm text-muted-foreground">{t("insights.missedSavings.subtitle")}</p>
      </div>

      {byBand.length === 0 ? (
        <p className="rounded-2xl bg-secondary p-4 text-sm text-muted-foreground">
          {t("insights.missedSavings.empty")}
        </p>
      ) : (
        byBand.map((group) => <BandCarousel key={group.band} band={group.band} shops={group.shops} />)
      )}
    </section>
  )
}

function BandCarousel({ band, shops }: { band: StoreMatchBand; shops: MissedShop[] }) {
  const { t, i18n } = useTranslation()
  const direction = getDirection(i18n.language)
  const [api, setApi] = useState<CarouselApi>()

  const labels = shops.map((shop) => shop.store_name)

  return (
    <div className="space-y-2 border-t border-border/70 pt-4 first:border-t-0 first:pt-0">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-bold", BAND_TONE[band])}>
            {t(`insights.missedSavings.band.${band}.label`)}
          </span>
          <p className="text-xs text-muted-foreground">{t(`insights.missedSavings.band.${band}.hint`)}</p>
        </div>
        <span className="shrink-0 text-xs font-semibold text-muted-foreground">
          {t("insights.missedSavings.shopCount", { count: shops.length })}
        </span>
      </div>

      <Carousel setApi={setApi} opts={{ align: "start", direction }}>
        <CarouselContent>
          {shops.map((shop) => (
            <CarouselItem key={shop.store_id}>
              <ShopSlide shop={shop} />
            </CarouselItem>
          ))}
        </CarouselContent>
        {shops.length > 1 && (
          <div className="mt-3 flex items-center justify-center gap-3">
            <CarouselPrevious aria-label={t("common.previousSlide")} />
            <CarouselDots api={api} labels={labels} />
            <CarouselNext aria-label={t("common.nextSlide")} />
          </div>
        )}
      </Carousel>
    </div>
  )
}

function ShopSlide({ shop }: { shop: MissedShop }) {
  const { t } = useTranslation()
  const topDeal = shop.deal_titles[0]

  return (
    <div className="flex h-[230px] flex-col gap-3 rounded-2xl bg-secondary p-4">
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-card text-lg">
          {emojiForStore(shop.store_name)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate font-bold">{shop.store_name}</p>
          <p className="text-xs text-muted-foreground">
            {t("insights.missedSavings.dealCount", { count: shop.deal_count })}
            {shop.also_known_as.length > 0 && ` · ${shop.also_known_as[0]}`}
          </p>
        </div>
      </div>

      {topDeal && <p className="line-clamp-2 text-xs text-muted-foreground">{topDeal}</p>}

      <div className="rounded-xl bg-card px-3 py-2">
        <p className="text-xs text-muted-foreground">
          {shop.is_same_store
            ? t("insights.missedSavings.coversHere", { count: shop.covered_transaction_count })
            : t("insights.missedSavings.coversSimilar", { count: shop.covered_transaction_count })}
        </p>
        <p className="font-bold">{formatAmount(shop.covered_amount)}</p>
      </div>

      <ul className="no-scrollbar min-h-0 flex-1 space-y-1 overflow-y-auto pe-1">
        {shop.purchases.slice(0, 6).map((purchase) => (
          <li
            key={purchase.transaction_id}
            className="flex items-center justify-between gap-2 text-xs text-muted-foreground"
          >
            <span className="truncate">{purchase.merchant_name}</span>
            <span className="shrink-0 font-medium">{formatAmount(purchase.amount)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
