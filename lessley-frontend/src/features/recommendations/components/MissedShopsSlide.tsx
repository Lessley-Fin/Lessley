import { useEffect, useMemo, useState } from "react"
import { ArrowLeft, ArrowRight, CreditCard, Store, Ticket } from "lucide-react"
import { useTranslation } from "react-i18next"

import { CarouselDots } from "@/components/shared/CarouselDots"
import { InfoDialog } from "@/components/shared/InfoDialog"
import { Button } from "@/components/ui/button"
import { Carousel, CarouselContent, CarouselItem, type CarouselApi } from "@/components/ui/carousel"
import { useClubs } from "@/features/clubs/hooks"
import { AnalysisPeriodCard } from "@/features/insights/components/AnalysisPeriodCard"
import { useAccounts } from "@/features/insights/hooks"
import { emojiForStore } from "@/lib/constants"
import { formatAmount } from "@/lib/formatters"
import { getDirection } from "@/lib/i18n/config"
import type { MissedShop, StoreMatchBand } from "@/lib/types"
import { cn } from "@/lib/utils"

/**
 * Shops running a deal the user's own spending could have covered.
 *
 * One card per confidence band, because the three do not mean the same thing and must not be
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

interface MerchantGroup {
  merchantName: string
  totalAmount: number
  transactionCount: number
  /** The accounts these purchases were charged to — the card the user actually paid with. */
  accountIds: string[]
  shops: MissedShop[]
}

/**
 * Shops carry their matched purchases, but the user thinks in terms of "what I bought" —
 * so invert that: one card per merchant they actually spent at, listing every deal-running
 * shop that purchase matched. A transaction can match more than one shop (a coffee purchase
 * can resemble several cafés under SIMILAR), so dedupe by transaction_id when summing spend —
 * otherwise the same purchase would be counted once per shop it happened to match.
 */
function groupByMerchant(shops: MissedShop[]): MerchantGroup[] {
  const groups = new Map<
    string,
    { totalAmount: number; transactionIds: Set<string>; accountIds: Set<string>; shops: Map<string, MissedShop> }
  >()

  for (const shop of shops) {
    for (const purchase of shop.purchases) {
      let group = groups.get(purchase.merchant_name)
      if (!group) {
        group = { totalAmount: 0, transactionIds: new Set(), accountIds: new Set(), shops: new Map() }
        groups.set(purchase.merchant_name, group)
      }
      if (!group.transactionIds.has(purchase.transaction_id)) {
        group.transactionIds.add(purchase.transaction_id)
        group.totalAmount += purchase.amount
        if (purchase.account_id) group.accountIds.add(purchase.account_id)
      }
      group.shops.set(shop.store_id, shop)
    }
  }

  return Array.from(groups, ([merchantName, group]) => ({
    merchantName,
    totalAmount: group.totalAmount,
    transactionCount: group.transactionIds.size,
    accountIds: Array.from(group.accountIds),
    shops: Array.from(group.shops.values()),
  }))
}

interface MissedShopsSlideProps {
  shops: MissedShop[]
  isLoading: boolean
  days: number
  onDaysChange: (days: number) => void
}

export function MissedShopsSlide({ shops, isLoading, days, onDaysChange }: MissedShopsSlideProps) {
  const { t } = useTranslation()
  const [chosenBand, setBand] = useState<StoreMatchBand>("EXACT")

  // The payload names an account and a club only by id. Both lists are fetched here and
  // resolved to names on the client, so the insight endpoint stays a set of ids and never
  // has to restate data the app already holds.
  const { data: accounts = [] } = useAccounts()
  const { data: clubs = [] } = useClubs()

  const accountNames = useMemo(() => {
    const named = new Map<string, string>()
    for (const account of accounts) {
      const label = [account.product, account.providerId].filter(Boolean).join(" · ")
      named.set(account.id, label || account.id)
    }
    return named
  }, [accounts])

  const clubNames = useMemo(() => new Map(clubs.map((club) => [club.id, club.name])), [clubs])

  const byBand = useMemo(() => {
    const grouped = {} as Record<StoreMatchBand, MissedShop[]>
    for (const key of BANDS) grouped[key] = shops.filter((shop) => shop.match_band === key)
    return grouped
  }, [shops])

  // Grouped once here (not per-band-card) so the tab counts and the header total are always
  // reading the same numbers as what the carousels actually render — one source of truth.
  const merchantsByBand = useMemo(() => {
    const grouped = {} as Record<StoreMatchBand, MerchantGroup[]>
    for (const key of BANDS) grouped[key] = groupByMerchant(byBand[key])
    return grouped
  }, [byBand])

  const totalMerchantCount = BANDS.reduce((sum, key) => sum + merchantsByBand[key].length, 0)

  // Fall through to a band that actually has something, so changing the period never leaves
  // the user staring at an empty tab. Derived rather than corrected after the fact — the
  // chosen band is remembered, and returns as soon as it has shops again.
  const band = byBand[chosenBand].length > 0 ? chosenBand : (BANDS.find((key) => byBand[key].length > 0) ?? chosenBand)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span className="flex size-10 items-center justify-center rounded-full bg-accent">
            <Store className="size-4 text-accent-foreground" aria-hidden />
          </span>
          <div className="flex-1">
            <p className="font-bold">{t("recommendations.missedShopsSlide.title")}</p>
            <p className="text-xs text-muted-foreground">
              {t("recommendations.missedShopsSlide.subtitle", { count: totalMerchantCount })}
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

        {!isLoading && shops.length > 0 && (
          <div className="no-scrollbar flex items-center gap-1 overflow-x-auto rounded-full border border-border bg-card p-1 text-sm">
            {BANDS.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setBand(key)}
                disabled={merchantsByBand[key].length === 0}
                className={cn(
                  "flex-1 rounded-full whitespace-nowrap px-3 py-2 font-medium transition-colors disabled:opacity-40",
                  band === key ? "surface-navy shadow-[var(--shadow-card)]" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {t(`recommendations.missedShopsSlide.band.${key}.label`)} ({merchantsByBand[key].length})
              </button>
            ))}
          </div>
        )}
      </div>

      {isLoading ? (
        <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground shadow-[var(--shadow-card)]">
          {t("recommendations.missedShopsSlide.loading")}
        </p>
      ) : shops.length === 0 ? (
        <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground shadow-[var(--shadow-card)]">
          {t("recommendations.missedShopsSlide.empty")}
        </p>
      ) : (
        <BandCard
          key={band}
          band={band}
          merchants={merchantsByBand[band]}
          accountNames={accountNames}
          clubNames={clubNames}
        />
      )}
    </div>
  )
}

interface NamesByIdProps {
  /** account id → "product · provider", read off the accounts the client fetched itself. */
  accountNames: Map<string, string>
  /** club id → club name. */
  clubNames: Map<string, string>
}

function BandCard({
  band,
  merchants,
  accountNames,
  clubNames,
}: { band: StoreMatchBand; merchants: MerchantGroup[] } & NamesByIdProps) {
  const { t, i18n } = useTranslation()
  const direction = getDirection(i18n.language)
  const [api, setApi] = useState<CarouselApi>()
  const [canScrollPrev, setCanScrollPrev] = useState(false)
  const [canScrollNext, setCanScrollNext] = useState(false)

  useEffect(() => {
    if (!api) return
    const onSelect = () => {
      setCanScrollPrev(api.canScrollPrev())
      setCanScrollNext(api.canScrollNext())
    }
    onSelect()
    api.on("select", onSelect)
    api.on("reInit", onSelect)
    return () => {
      api.off("select", onSelect)
      api.off("reInit", onSelect)
    }
  }, [api])

  return (
    <div className="flex flex-col gap-2 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="text-xs text-muted-foreground">{t(`recommendations.missedShopsSlide.band.${band}.hint`)}</p>

      <Carousel setApi={setApi} opts={{ align: "start", direction }}>
        <CarouselContent>
          {merchants.map((merchant) => (
            <CarouselItem key={merchant.merchantName}>
              <TransactionCard merchant={merchant} accountNames={accountNames} clubNames={clubNames} />
            </CarouselItem>
          ))}
        </CarouselContent>
      </Carousel>

      {merchants.length > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button
            type="button"
            variant="pill"
            size="icon"
            className="size-8 shrink-0"
            onClick={() => api?.scrollPrev()}
            disabled={!canScrollPrev}
            aria-label={t("common.previousSlide")}
          >
            {direction === "rtl" ? <ArrowRight aria-hidden /> : <ArrowLeft aria-hidden />}
          </Button>
          <CarouselDots api={api} labels={merchants.map((merchant) => merchant.merchantName)} />
          <Button
            type="button"
            variant="pill"
            size="icon"
            className="size-8 shrink-0"
            onClick={() => api?.scrollNext()}
            disabled={!canScrollNext}
            aria-label={t("common.nextSlide")}
          >
            {direction === "rtl" ? <ArrowLeft aria-hidden /> : <ArrowRight aria-hidden />}
          </Button>
        </div>
      )}
    </div>
  )
}

function TransactionCard({
  merchant,
  accountNames,
  clubNames,
}: { merchant: MerchantGroup } & NamesByIdProps) {
  const { t } = useTranslation()

  // Where the money came from. An unknown id still gets shown rather than dropped — a card
  // the accounts list no longer covers is worth saying out loud, not silently hiding.
  const sources = merchant.accountIds.map((id) => accountNames.get(id) ?? id)

  return (
    <div className="flex h-72 flex-col gap-3 rounded-2xl bg-secondary p-4">
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-card text-lg">
          {emojiForStore(merchant.merchantName)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">{merchant.merchantName}</p>
          <p className="text-xs text-muted-foreground">
            {t("recommendations.missedShopsSlide.purchaseCount", { count: merchant.transactionCount })}
          </p>
          {sources.length > 0 && (
            <p className="mt-1 flex items-start gap-1 text-[11px] text-muted-foreground">
              <CreditCard className="mt-px size-3 shrink-0" aria-hidden />
              <span className="min-w-0 break-words">
                {t("recommendations.missedShopsSlide.paidWith", { sources: sources.join(", ") })}
              </span>
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-0.5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {t("recommendations.missedShopsSlide.spentLabel")}
          </p>
          <span className="rounded-full bg-card px-2.5 py-1 text-sm font-bold">
            {formatAmount(merchant.totalAmount)}
          </span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-1">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {t("recommendations.missedShopsSlide.matchingShopsHeading", { count: merchant.shops.length })}
        </p>
        <ul className="no-scrollbar min-h-0 flex-1 space-y-1.5 overflow-y-auto">
          {merchant.shops.map((shop) => {
            // The club is the whole point of the row: the deal existed and the user is a
            // member, so naming the club is what tells them how they could have claimed it.
            const missedClubs = shop.club_ids.map((id) => clubNames.get(id) ?? id)

            return (
              <li key={shop.store_id} className="flex items-start gap-2 rounded-xl bg-card px-2.5 py-2">
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full text-xs",
                    BAND_TONE[shop.match_band],
                  )}
                >
                  {emojiForStore(shop.store_name)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold">{shop.store_name}</p>
                  {shop.deal_titles[0] && (
                    <p className="line-clamp-1 text-[11px] text-muted-foreground">{shop.deal_titles[0]}</p>
                  )}
                  {missedClubs.length > 0 && (
                    <p className="mt-0.5 flex items-start gap-1 text-[11px] text-muted-foreground">
                      <Ticket className="mt-px size-3 shrink-0" aria-hidden />
                      <span className="min-w-0 break-words">
                        {t("recommendations.missedShopsSlide.missedClub", { clubs: missedClubs.join(", ") })}
                      </span>
                    </p>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
