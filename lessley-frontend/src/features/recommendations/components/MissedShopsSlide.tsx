import { useEffect, useState } from "react"
import { Store } from "lucide-react"
import { useTranslation } from "react-i18next"

import { InfoDialog } from "@/components/shared/InfoDialog"
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
 * Shops running a deal the user's own spending could have covered.
 *
 * One carousel per confidence band, because the three do not mean the same thing and must not
 * be read as though they did. An EXACT or STRONG shop is the one the user walked into, so
 * "you missed a coupon here" is simply true. A SIMILAR shop only shares a word naming a line
 * of business — 'קפה ברלין' against 'קפה קפה' — so it is somewhere *like* theirs, and saying
 * they shopped there would be false. Separate carousels are what stop the weaker claim
 * borrowing the stronger one's credibility.
 */

const BAND_ORDER: StoreMatchBand[] = ["EXACT", "SIMILAR", "STRONG"]

const BAND_TONE: Record<StoreMatchBand, string> = {
  EXACT: "bg-emerald-500/12 text-emerald-600 dark:text-emerald-400",
  STRONG: "bg-sky-500/12 text-sky-600 dark:text-sky-400",
  SIMILAR: "bg-amber-500/12 text-amber-600 dark:text-amber-500",
}

interface MissedShopsSlideProps {
  shops: MissedShop[]
  isLoading: boolean
}

export function MissedShopsSlide({ shops, isLoading }: MissedShopsSlideProps) {
  const { t } = useTranslation()

  const byBand = BAND_ORDER.map((band) => ({
    band,
    shops: shops.filter((shop) => shop.match_band === band),
  })).filter((group) => group.shops.length > 0)

  return (
    <div className="flex h-[420px] flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
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

      {isLoading ? (
        <p className="text-sm text-muted-foreground">{t("recommendations.missedShopsSlide.loading")}</p>
      ) : byBand.length === 0 ? (
        <p className="rounded-2xl bg-secondary p-4 text-sm text-muted-foreground">
          {t("recommendations.missedShopsSlide.empty")}
        </p>
      ) : (
        <div className="no-scrollbar min-h-0 flex-1 space-y-4 overflow-y-auto pe-1">
          {byBand.map((group) => (
            <BandCarousel key={group.band} band={group.band} shops={group.shops} />
          ))}
        </div>
      )}
    </div>
  )
}

function BandCarousel({ band, shops }: { band: StoreMatchBand; shops: MissedShop[] }) {
  const { t, i18n } = useTranslation()
  const direction = getDirection(i18n.language)
  const [api, setApi] = useState<CarouselApi>()
  const [selected, setSelected] = useState(0)

  useEffect(() => {
    if (!api) return
    const onSelect = () => setSelected(api.selectedScrollSnap())
    onSelect()
    api.on("select", onSelect)
    return () => {
      api.off("select", onSelect)
    }
  }, [api])

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-bold", BAND_TONE[band])}>
          {t(`recommendations.missedShopsSlide.band.${band}.label`)}
        </span>
        <p className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
          {t(`recommendations.missedShopsSlide.band.${band}.hint`)}
        </p>
        <span className="shrink-0 text-xs font-semibold tabular-nums text-muted-foreground">
          {selected + 1}/{shops.length}
        </span>
      </div>

      <Carousel setApi={setApi} opts={{ align: "start", direction }}>
        <CarouselContent>
          {shops.map((shop) => (
            <CarouselItem key={shop.store_id}>
              <ShopCard shop={shop} />
            </CarouselItem>
          ))}
        </CarouselContent>
        {shops.length > 1 && (
          <div className="mt-2 flex items-center justify-center gap-3">
            <CarouselPrevious aria-label={t("common.previousSlide")} />
            <CarouselNext aria-label={t("common.nextSlide")} />
          </div>
        )}
      </Carousel>
    </section>
  )
}

function ShopCard({ shop }: { shop: MissedShop }) {
  const { t } = useTranslation()
  const topDeal = shop.deal_titles[0]

  return (
    <div className="space-y-2 rounded-2xl bg-secondary p-3">
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

      <ul className="space-y-0.5">
        {shop.purchases.slice(0, 3).map((purchase) => (
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
