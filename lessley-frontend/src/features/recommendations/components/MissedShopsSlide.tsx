import { useEffect, useState } from "react"
import { ArrowLeft, ArrowRight, BadgePercent, CreditCard, Ticket, TicketPercent } from "lucide-react"
import { useTranslation } from "react-i18next"

import { CarouselDots } from "@/components/shared/CarouselDots"
import { InfoDialog } from "@/components/shared/InfoDialog"
import { Button } from "@/components/ui/button"
import { Carousel, CarouselContent, CarouselItem, type CarouselApi } from "@/components/ui/carousel"
import { useClubs } from "@/features/clubs/hooks"
import { AnalysisPeriodCard } from "@/features/insights/components/AnalysisPeriodCard"
import { useAccounts } from "@/features/insights/hooks"
import { resolveClubName } from "@/lib/clubs"
import { emojiForStore } from "@/lib/constants"
import { formatAmount } from "@/lib/formatters"
import { getDirection } from "@/lib/i18n/config"
import type { MissedSavings, SavingsBand, SavingsMerchant, StoreMatchBand } from "@/lib/types"
import { cn } from "@/lib/utils"

/**
 * Money the user spent at full price while a deal they were entitled to was running.
 *
 * The subject is the loss, not the match: every card names what they paid, how many deals were
 * live at the time, and which of their clubs would have covered it.
 *
 * One card per confidence band, because the three do not mean the same thing and must not be
 * read as though they did. An EXACT or STRONG shop is the one the user walked into, so "you
 * paid full price here" is simply true. A SIMILAR shop only shares a word naming a line of
 * business — 'קפה ברלין' against 'קפה קפה' — so it is somewhere *like* theirs, and saying they
 * shopped there would be false: that band is worded as a tip for next time, never as a
 * discount they lost.
 *
 * **This component computes nothing.** Every figure — the header total, each band's subtotal,
 * each merchant's count and amount — arrives already worked out. It used to invert shops into
 * merchants, dedupe them and total them here, and that second implementation of the service's
 * rules is how the screen came to disagree with the service and with itself: a purchase
 * matching three shops was counted three times, and the band tabs added up to more than the
 * headline with nothing on screen to explain the gap. If a number is missing, it goes in the
 * payload — never into a `reduce` here.
 */

const BAND_TONE: Record<StoreMatchBand, string> = {
  EXACT: "bg-emerald-500/12 text-emerald-600 dark:text-emerald-400",
  STRONG: "bg-sky-500/12 text-sky-600 dark:text-sky-400",
  SIMILAR: "bg-amber-500/12 text-amber-600 dark:text-amber-500",
}

interface MissedShopsSlideProps {
  missed: MissedSavings
  isLoading: boolean
  days: number
  onDaysChange: (days: number) => void
}

export function MissedShopsSlide({ missed, isLoading, days, onDaysChange }: MissedShopsSlideProps) {
  const { t } = useTranslation()
  const [chosenBand, setBand] = useState<StoreMatchBand | null>(null)

  // The payload names an account and a club only by id. Both lists are fetched here and
  // resolved to names on the client, so the insight endpoint stays a set of ids and never has
  // to restate data the app already holds. Naming is not arithmetic.
  const { data: accounts = [] } = useAccounts()
  const { data: clubs = [] } = useClubs()

  const accountNames = new Map(
    accounts.map((account) => [account.id, [account.product, account.providerId].filter(Boolean).join(" · ") || account.id]),
  )
  // resolveClubName rather than a plain id→name map: a shop can carry a `club_`-prefixed id, a
  // scraper source id, or a tiered `_regular`/`_vip` variant, and none of those key straight
  // into the clubs collection's own ids.
  const clubNames = (id: string) => resolveClubName(clubs, id) ?? id

  // The service returns only the bands that have something in them, in confidence order.
  // Falling through to the first keeps the user off an empty tab when the period changes,
  // while remembering the one they picked for as long as it has merchants.
  const bands = missed.bands
  const band = bands.find((row) => row.band === chosenBand) ?? bands[0]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span className="flex size-10 items-center justify-center rounded-full bg-accent">
            <BadgePercent className="size-4 text-accent-foreground" aria-hidden />
          </span>
          <div className="flex-1">
            <p className="font-bold">{t("recommendations.missedShopsSlide.title")}</p>
            <p className="text-xs text-muted-foreground">
              {t("recommendations.missedShopsSlide.subtitle", {
                count: missed.purchase_count,
                amount: formatAmount(missed.total_amount),
              })}
            </p>
          </div>
          <InfoDialog
            ariaLabel={t("recommendations.missedShopsSlide.infoDialog.ariaLabel")}
            title={t("recommendations.missedShopsSlide.infoDialog.title")}
          >
            <div className="flex flex-col gap-3 text-sm text-muted-foreground">
              <p>{t("recommendations.missedShopsSlide.infoDialog.intro")}</p>
              {/* The bands are spelled out under the same labels the tabs use, so the
                  explanation and the thing explained are recognisably the same words. */}
              <p>
                <span className="font-semibold text-foreground">
                  {t("recommendations.missedShopsSlide.band.EXACT.label")} ·{" "}
                  {t("recommendations.missedShopsSlide.band.STRONG.label")}
                </span>{" "}
                — {t("recommendations.missedShopsSlide.infoDialog.exact")}
              </p>
              <p>
                <span className="font-semibold text-foreground">
                  {t("recommendations.missedShopsSlide.band.SIMILAR.label")}
                </span>{" "}
                — {t("recommendations.missedShopsSlide.infoDialog.similar")}
              </p>
              {/* Both halves of the arithmetic a user would otherwise have to work out alone. */}
              <p>{t("recommendations.missedShopsSlide.infoDialog.bandsAddUp")}</p>
              <p>{t("recommendations.missedShopsSlide.infoDialog.applied")}</p>
            </div>
          </InfoDialog>
        </div>

        <AnalysisPeriodCard value={days} onChange={onDaysChange} />

        {!isLoading && bands.length > 0 && (
          <div className="no-scrollbar flex items-center gap-1 overflow-x-auto rounded-full border border-border bg-card p-1 text-sm">
            {bands.map((row) => (
              <button
                key={row.band}
                type="button"
                onClick={() => setBand(row.band)}
                className={cn(
                  "flex-1 rounded-full whitespace-nowrap px-3 py-2 font-medium transition-colors",
                  band?.band === row.band
                    ? "surface-navy shadow-[var(--shadow-card)]"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {t(`recommendations.missedShopsSlide.band.${row.band}.label`)} ({row.purchase_count})
              </button>
            ))}
          </div>
        )}
      </div>

      {isLoading ? (
        <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground shadow-[var(--shadow-card)]">
          {t("recommendations.missedShopsSlide.loading")}
        </p>
      ) : !band ? (
        <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground shadow-[var(--shadow-card)]">
          {t("recommendations.missedShopsSlide.empty")}
        </p>
      ) : (
        <BandCard key={band.band} band={band} accountNames={accountNames} clubNames={clubNames} />
      )}
    </div>
  )
}

interface NamesByIdProps {
  /** account id → "product · provider", read off the accounts the client fetched itself. */
  accountNames: Map<string, string>
  /** club id → club name. */
  clubNames: (id: string) => string
}

function BandCard({ band, accountNames, clubNames }: { band: SavingsBand } & NamesByIdProps) {
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
      <p className="text-xs text-muted-foreground">
        {t(`recommendations.missedShopsSlide.band.${band.band}.hint`)}
      </p>

      <Carousel setApi={setApi} opts={{ align: "start", direction }}>
        <CarouselContent>
          {band.merchants.map((merchant) => (
            <CarouselItem key={merchant.merchant_name}>
              <MerchantCard merchant={merchant} accountNames={accountNames} clubNames={clubNames} />
            </CarouselItem>
          ))}
        </CarouselContent>
      </Carousel>

      {band.merchants.length > 1 && (
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
          <CarouselDots api={api} labels={band.merchants.map((merchant) => merchant.merchant_name)} />
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

function MerchantCard({
  merchant,
  accountNames,
  clubNames,
}: { merchant: SavingsMerchant } & NamesByIdProps) {
  const { t } = useTranslation()
  const band = merchant.band as StoreMatchBand

  // Where the money came from. An unknown id still gets shown rather than dropped — a card
  // the accounts list no longer covers is worth saying out loud, not silently hiding.
  const sources = merchant.account_ids.map((id) => accountNames.get(id) ?? id)

  return (
    <div className="flex h-80 flex-col gap-3 rounded-2xl bg-secondary p-4">
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-card text-lg">
          {emojiForStore(merchant.merchant_name)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">{merchant.merchant_name}</p>
          <p className="text-xs text-muted-foreground">
            {t("recommendations.missedShopsSlide.purchaseCount", { count: merchant.purchase_count })}
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
            {formatAmount(merchant.amount)}
          </span>
        </div>
      </div>

      {/* The loss, stated once and in the band's own terms — full price paid for EXACT and
          STRONG, a heads-up for next time for SIMILAR, where the user never shopped. */}
      <p className={cn("flex items-start gap-2 rounded-xl px-3 py-2 text-[11px] font-medium", BAND_TONE[band])}>
        <TicketPercent className="mt-px size-3.5 shrink-0" aria-hidden />
        <span className="min-w-0">
          {t(`recommendations.missedShopsSlide.band.${band}.callout`, { count: merchant.deal_count })}
        </span>
      </p>

      <div className="flex min-h-0 flex-1 flex-col gap-1">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {t(`recommendations.missedShopsSlide.band.${band}.shopsHeading`)}
        </p>
        <ul className="no-scrollbar min-h-0 flex-1 space-y-1.5 overflow-y-auto">
          {merchant.shops.map((shop) => {
            // The club is the whole point of the row: the deal existed and the user is a
            // member, so naming the club is what tells them how they could have claimed it.
            const missedClubs = shop.club_ids.map((id) => clubNames(id))

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
