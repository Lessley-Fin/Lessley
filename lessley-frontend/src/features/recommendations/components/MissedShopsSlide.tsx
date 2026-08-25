import { useEffect, useMemo, useState } from "react"
import { ArrowLeft, ArrowRight, BadgePercent, CreditCard, PiggyBank, Ticket, TicketPercent } from "lucide-react"
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
 * Money the user spent at full price while a deal they were entitled to was running.
 *
 * The subject is the loss, not the match: every card names what they paid, how many deals were
 * live at the time, and which of their clubs would have covered it. The copy says that outright
 * — an insight the user has to decode is an insight they scroll past.
 *
 * One card per confidence band, because the three do not mean the same thing and must not be
 * read as though they did. An EXACT or STRONG shop is the one the user walked into, so "you
 * paid full price here" is simply true. A SIMILAR shop only shares a word naming a line of
 * business — 'קפה ברלין' against 'קפה קפה' — so it is somewhere *like* theirs, and saying
 * they shopped there would be false: that band is worded as a tip for next time, never as a
 * discount they lost. Separating them is what stops the weaker claim borrowing the stronger
 * one's credibility.
 */

const BANDS: StoreMatchBand[] = ["EXACT", "SIMILAR", "STRONG"]

/**
 * The settled tab, sitting at the end of the band strip.
 *
 * Not a band — the bands grade how sure we are that a shop is the user's, and this one is not
 * a question of confidence at all: a club's benefit card either paid or it did not. It shares
 * the strip because from the user's side the strip answers "which list am I looking at", and
 * splitting that control in two to honour an internal distinction would be the tail wagging
 * the dog. Everything downstream that keys off a band has to allow for this value, which is
 * why it is a separate type rather than a fourth member of `StoreMatchBand`.
 */
const SETTLED = "SETTLED" as const

type Tab = StoreMatchBand | typeof SETTLED

const TABS: Tab[] = [...BANDS, SETTLED]

const BAND_TONE: Record<StoreMatchBand, string> = {
  EXACT: "bg-emerald-500/12 text-emerald-600 dark:text-emerald-400",
  STRONG: "bg-sky-500/12 text-sky-600 dark:text-sky-400",
  SIMILAR: "bg-amber-500/12 text-amber-600 dark:text-amber-500",
}

interface MerchantGroup {
  merchantName: string
  /** What went unclaimed here. The headline figure — "you paid" means this. */
  missedAmount: number
  missedTransactionCount: number
  /** What a club's own card already knocked off here. The opposite of a loss. */
  committedAmount: number
  committedTransactionCount: number
  committedClubIds: string[]
  /** Deals live across every matched shop — the size of what went unclaimed. */
  dealCount: number
  /** The accounts these purchases were charged to — the card the user actually paid with. */
  accountIds: string[]
  shops: MissedShop[]
}

/**
 * A purchase settled at one matched shop is settled at every shop that matched it.
 *
 * The backend answers per shop, and it is right to: the club card paid at the shop the user
 * walked into, not at the lookalike café the name also resembled, so only the first shop's
 * copy of the purchase carries the clubs. But every list on this screen is cut from a subset
 * of shops — one band at a time — and a subset that happens to exclude the shop holding the
 * settlement would read the very same purchase as a loss. Fold the clubs onto every copy up
 * front, once, so no later grouping can disagree with another about what the user paid.
 */
function settleAcrossShops(shops: MissedShop[]): MissedShop[] {
  const clubsByTransaction = new Map<string, Set<string>>()
  for (const shop of shops) {
    for (const purchase of shop.purchases) {
      const covered = purchase.covered_by_club_ids ?? []
      if (covered.length === 0) continue
      const known = clubsByTransaction.get(purchase.transaction_id) ?? new Set<string>()
      for (const clubId of covered) known.add(clubId)
      clubsByTransaction.set(purchase.transaction_id, known)
    }
  }

  if (clubsByTransaction.size === 0) return shops

  return shops.map((shop) => ({
    ...shop,
    purchases: shop.purchases.map((purchase) => {
      const clubs = clubsByTransaction.get(purchase.transaction_id)
      return clubs ? { ...purchase, covered_by_club_ids: Array.from(clubs) } : purchase
    }),
  }))
}

/**
 * Shops carry their matched purchases, but the user thinks in terms of "what I bought" —
 * so invert that: one card per merchant they actually spent at, listing every deal-running
 * shop that purchase matched. A transaction can match more than one shop (a coffee purchase
 * can resemble several cafés under SIMILAR), so count each one once however many shops it
 * matched — otherwise the same purchase is counted once per lookalike.
 *
 * Spend splits in two. A purchase charged to a club's own benefit card already took the
 * discount, so it is money *saved*, not missed, and adding it to the loss would tell the user
 * they lost out on the one occasion they did everything right. Which side a purchase falls on
 * is settled before this runs — see {@link settleAcrossShops}.
 */
function groupByMerchant(shops: MissedShop[]): MerchantGroup[] {
  const groups = new Map<
    string,
    {
      missedAmount: number
      committedAmount: number
      missedIds: Set<string>
      committedIds: Set<string>
      accountIds: Set<string>
      committedClubIds: Set<string>
      shops: Map<string, MissedShop>
    }
  >()

  for (const shop of shops) {
    for (const purchase of shop.purchases) {
      let group = groups.get(purchase.merchant_name)
      if (!group) {
        group = {
          missedAmount: 0,
          committedAmount: 0,
          missedIds: new Set(),
          committedIds: new Set(),
          accountIds: new Set(),
          committedClubIds: new Set(),
          shops: new Map(),
        }
        groups.set(purchase.merchant_name, group)
      }

      // Every shop the purchase matched belongs on the card, even the second sighting of it.
      group.shops.set(shop.store_id, shop)
      if (purchase.account_id) group.accountIds.add(purchase.account_id)

      const covered = purchase.covered_by_club_ids ?? []
      for (const clubId of covered) group.committedClubIds.add(clubId)

      if (group.missedIds.has(purchase.transaction_id) || group.committedIds.has(purchase.transaction_id)) {
        continue
      }
      if (covered.length > 0) {
        group.committedIds.add(purchase.transaction_id)
        group.committedAmount += purchase.amount
      } else {
        group.missedIds.add(purchase.transaction_id)
        group.missedAmount += purchase.amount
      }
    }
  }

  return Array.from(groups, ([merchantName, group]) => {
    const shops = Array.from(group.shops.values())
    return {
      merchantName,
      missedAmount: group.missedAmount,
      missedTransactionCount: group.missedIds.size,
      committedAmount: group.committedAmount,
      committedTransactionCount: group.committedIds.size,
      committedClubIds: Array.from(group.committedClubIds),
      dealCount: shops.reduce((sum, shop) => sum + shop.deal_count, 0),
      accountIds: Array.from(group.accountIds),
      shops,
    }
  })
}

/** Nothing left to claim here — every matching purchase already used a club card. */
const isFullySettled = (merchant: MerchantGroup) => merchant.missedTransactionCount === 0

interface MissedShopsSlideProps {
  shops: MissedShop[]
  isLoading: boolean
  days: number
  onDaysChange: (days: number) => void
}

export function MissedShopsSlide({ shops, isLoading, days, onDaysChange }: MissedShopsSlideProps) {
  const { t } = useTranslation()
  const [chosenTab, setTab] = useState<Tab>("EXACT")

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

  // Settled first, then sliced: every list below is cut from a subset of shops, and they must
  // all agree about which purchases the club card already paid for.
  const settledShops = useMemo(() => settleAcrossShops(shops), [shops])

  const byBand = useMemo(() => {
    const grouped = {} as Record<StoreMatchBand, MissedShop[]>
    for (const key of BANDS) grouped[key] = settledShops.filter((shop) => shop.match_band === key)
    return grouped
  }, [settledShops])

  // Grouped once here (not per-band-card) so the tab counts and the header total are always
  // reading the same numbers as what the carousels actually render — one source of truth.
  //
  // A merchant with nothing left to claim is dropped from the bands: they are headed
  // "discounts you missed", and a purchase that already used the club card did not miss one.
  // It is not thrown away — the settled tab picks it up.
  const merchantsByBand = useMemo(() => {
    const grouped = {} as Record<StoreMatchBand, MerchantGroup[]>
    for (const key of BANDS) grouped[key] = groupByMerchant(byBand[key]).filter((m) => !isFullySettled(m))
    return grouped
  }, [byBand])

  // Grouped over *all* shops rather than summed across the per-band groups: one merchant can
  // match an EXACT shop and a SIMILAR one at once, and adding the bands up would count that
  // merchant — and its spend — twice in the one number the user reads first.
  const allMerchants = useMemo(() => groupByMerchant(settledShops), [settledShops])
  const missedMerchants = allMerchants.filter((merchant) => !isFullySettled(merchant))

  // Every merchant a club card paid at, not only the ones the bands dropped. A partly-settled
  // merchant therefore appears under its band *and* here — but the two tabs answer different
  // questions and show different money, and only one is on screen at a time. Showing half the
  // savings to avoid the overlap would make this tab a worse answer than no tab at all.
  const settledMerchants = allMerchants.filter((merchant) => merchant.committedTransactionCount > 0)

  const counts = useMemo(() => {
    const byTab = {} as Record<Tab, number>
    for (const key of BANDS) byTab[key] = merchantsByBand[key].length
    byTab[SETTLED] = settledMerchants.length
    return byTab
  }, [merchantsByBand, settledMerchants.length])

  // Fall through to a tab that actually has something, so changing the period never leaves the
  // user staring at an empty one. Derived rather than corrected after the fact — the chosen
  // tab is remembered, and returns as soon as it has merchants again.
  //
  // Settled sits last in the order, so a period where the user missed nothing but did save
  // lands here on its own, which is exactly the right thing to open on.
  const tab = counts[chosenTab] > 0 ? chosenTab : (TABS.find((key) => counts[key] > 0) ?? chosenTab)

  // The header speaks for whichever tab is open. A subtitle totalling missed money while the
  // user reads a list of savings they made is not a small inconsistency — it is the exact
  // confusion this whole change exists to remove.
  const isSettled = tab === SETTLED
  const headlineMerchants = isSettled ? settledMerchants : missedMerchants
  const headlineAmount = headlineMerchants.reduce(
    (sum, merchant) => sum + (isSettled ? merchant.committedAmount : merchant.missedAmount),
    0,
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "flex size-10 items-center justify-center rounded-full",
              isSettled ? "bg-emerald-500/12" : "bg-accent",
            )}
          >
            {isSettled ? (
              <PiggyBank className="size-4 text-emerald-600 dark:text-emerald-400" aria-hidden />
            ) : (
              <BadgePercent className="size-4 text-accent-foreground" aria-hidden />
            )}
          </span>
          <div className="flex-1">
            <p className="font-bold">
              {t(isSettled ? "recommendations.missedShopsSlide.settled.title" : "recommendations.missedShopsSlide.title")}
            </p>
            <p className="text-xs text-muted-foreground">
              {t(
                isSettled
                  ? "recommendations.missedShopsSlide.settled.subtitle"
                  : "recommendations.missedShopsSlide.subtitle",
                { count: headlineMerchants.length, amount: formatAmount(headlineAmount) },
              )}
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
              <p>
                <span className="font-semibold text-foreground">
                  {t("recommendations.missedShopsSlide.settled.tabLabel")}
                </span>{" "}
                — {t("recommendations.missedShopsSlide.infoDialog.settled")}
              </p>
            </div>
          </InfoDialog>
        </div>

        <AnalysisPeriodCard value={days} onChange={onDaysChange} />

        {!isLoading && allMerchants.length > 0 && (
          <div className="no-scrollbar flex items-center gap-1 overflow-x-auto rounded-full border border-border bg-card p-1 text-sm">
            {TABS.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                disabled={counts[key] === 0}
                className={cn(
                  "flex-1 rounded-full whitespace-nowrap px-3 py-2 font-medium transition-colors disabled:opacity-40",
                  tab === key ? "surface-navy shadow-[var(--shadow-card)]" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {t(
                  key === SETTLED
                    ? "recommendations.missedShopsSlide.settled.tabLabel"
                    : `recommendations.missedShopsSlide.band.${key}.label`,
                )}{" "}
                ({counts[key]})
              </button>
            ))}
          </div>
        )}
      </div>

      {isLoading ? (
        <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground shadow-[var(--shadow-card)]">
          {t("recommendations.missedShopsSlide.loading")}
        </p>
      ) : allMerchants.length === 0 ? (
        <p className="rounded-3xl bg-card p-5 text-sm text-muted-foreground shadow-[var(--shadow-card)]">
          {t("recommendations.missedShopsSlide.empty")}
        </p>
      ) : isSettled ? (
        <SettledCard
          merchants={settledMerchants}
          nothingMissed={missedMerchants.length === 0}
          clubNames={clubNames}
        />
      ) : (
        <BandCard
          key={tab}
          band={tab}
          merchants={merchantsByBand[tab]}
          accountNames={accountNames}
          clubNames={clubNames}
        />
      )}
    </div>
  )
}

/**
 * The savings the user did make — purchases charged to a club's own benefit card, where the
 * discount came off at the till.
 *
 * Deliberately plain next to the band carousels above. There is nothing to act on here and no
 * confidence to qualify: a benefit card either paid or it did not. It earns its place because
 * these merchants would otherwise vanish between one period and the next with no explanation,
 * and because "you already saved here" is worth reading.
 */
function SettledCard({
  merchants,
  nothingMissed,
  clubNames,
}: { merchants: MerchantGroup[]; nothingMissed: boolean } & Pick<NamesByIdProps, "clubNames">) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col gap-2 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="text-xs text-muted-foreground">{t("recommendations.missedShopsSlide.settled.hint")}</p>

      {/* Two different nothings. Having matched no deal at all is not the same as having
          claimed every one of them, and only the second is worth congratulating. */}
      {nothingMissed && (
        <p className="flex items-start gap-2 rounded-xl bg-emerald-500/12 px-3 py-2 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
          <PiggyBank className="mt-px size-3.5 shrink-0" aria-hidden />
          <span className="min-w-0">{t("recommendations.missedShopsSlide.settled.nothingLeft")}</span>
        </p>
      )}

      {/* A plain list, where the band tabs get a carousel. There is nothing to act on per
          merchant here — no deal to claim, no confidence to weigh — so paging through them
          one at a time would be ceremony over a receipt. */}
      <ul className="space-y-1.5">
        {merchants.map((merchant) => {
          const clubs = merchant.committedClubIds.map((id) => clubNames.get(id) ?? id)

          return (
            <li key={merchant.merchantName} className="flex items-start gap-2 rounded-xl bg-secondary px-2.5 py-2">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-card text-xs">
                {emojiForStore(merchant.merchantName)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold">{merchant.merchantName}</p>
                <p className="text-[11px] text-muted-foreground">
                  {t("recommendations.missedShopsSlide.purchaseCount", {
                    count: merchant.committedTransactionCount,
                  })}
                  {clubs.length > 0 && ` · ${t("recommendations.missedShopsSlide.settled.withClub", { clubs: clubs.join(", ") })}`}
                </p>
              </div>
              <span className="shrink-0 rounded-full bg-card px-2.5 py-1 text-xs font-bold">
                {formatAmount(merchant.committedAmount)}
              </span>
            </li>
          )
        })}
      </ul>
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
              <TransactionCard band={band} merchant={merchant} accountNames={accountNames} clubNames={clubNames} />
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
  band,
  merchant,
  accountNames,
  clubNames,
}: { band: StoreMatchBand; merchant: MerchantGroup } & NamesByIdProps) {
  const { t } = useTranslation()

  // Where the money came from. An unknown id still gets shown rather than dropped — a card
  // the accounts list no longer covers is worth saying out loud, not silently hiding.
  const sources = merchant.accountIds.map((id) => accountNames.get(id) ?? id)

  // Which club's card already paid off here, for the merchants that are only partly settled.
  const settledClubs = merchant.committedClubIds.map((id) => clubNames.get(id) ?? id)

  return (
    <div className="flex h-80 flex-col gap-3 rounded-2xl bg-secondary p-4">
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-card text-lg">
          {emojiForStore(merchant.merchantName)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">{merchant.merchantName}</p>
          <p className="text-xs text-muted-foreground">
            {t("recommendations.missedShopsSlide.purchaseCount", { count: merchant.missedTransactionCount })}
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
            {formatAmount(merchant.missedAmount)}
          </span>
        </div>
      </div>

      {/* The loss, stated once and in the band's own terms — full price paid for EXACT and
          STRONG, a heads-up for next time for SIMILAR, where the user never shopped. */}
      <p className={cn("flex items-start gap-2 rounded-xl px-3 py-2 text-[11px] font-medium", BAND_TONE[band])}>
        <TicketPercent className="mt-px size-3.5 shrink-0" aria-hidden />
        <span className="min-w-0">
          {t(`recommendations.missedShopsSlide.band.${band}.callout`, { count: merchant.dealCount })}
        </span>
      </p>

      {/* Partly settled: some of these purchases did use the club card. Saying only what was
          lost would read as a scolding for a habit the user is already half in. */}
      {merchant.committedTransactionCount > 0 && (
        <p className="flex items-start gap-2 rounded-xl bg-emerald-500/12 px-3 py-2 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
          <PiggyBank className="mt-px size-3.5 shrink-0" aria-hidden />
          <span className="min-w-0">
            {t("recommendations.missedShopsSlide.settled.alsoHere", {
              count: merchant.committedTransactionCount,
              amount: formatAmount(merchant.committedAmount),
              clubs: settledClubs.join(", "),
            })}
          </span>
        </p>
      )}

      <div className="flex min-h-0 flex-1 flex-col gap-1">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {t(`recommendations.missedShopsSlide.band.${band}.shopsHeading`)}
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
