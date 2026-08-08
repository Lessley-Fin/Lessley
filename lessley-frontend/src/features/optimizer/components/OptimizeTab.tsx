import { useState } from "react"
import { Check, Loader2, Search, Sparkles, Store } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import type { StoreDocument } from "@/lib/types"
import { useOptimizeCart, useStoreSearch } from "../hooks"
import type { OptimizeParams } from "../api"
import { RankedOptions } from "./RankedOptions"
import { WinningStack } from "./WinningStack"

/** Card-shaped one-liner used for the prompt / loading / empty / error states. */
function Notice({ children, tone }: { children: React.ReactNode; tone?: "error" }) {
  return (
    <p
      className={cn(
        "rounded-3xl bg-card p-6 text-center text-sm shadow-[var(--shadow-card)]",
        tone === "error" ? "text-destructive" : "text-muted-foreground"
      )}
    >
      {children}
    </p>
  )
}

export function OptimizeTab() {
  const { t } = useTranslation()
  const [storeText, setStoreText] = useState("")
  const [selectedStore, setSelectedStore] = useState<StoreDocument | null>(null)
  const [cartTotal, setCartTotal] = useState("")
  const [submitted, setSubmitted] = useState<{ params: OptimizeParams; storeName: string } | null>(null)

  // Searching while a store is picked would re-open the suggestion list under the user.
  const { data: stores = [], isFetching: isSearchingStores } = useStoreSearch(selectedStore ? "" : storeText)
  const { data, isLoading, error } = useOptimizeCart(submitted?.params ?? null)

  const total = Number(cartTotal)
  const canSubmit = selectedStore !== null && Number.isFinite(total) && total > 0

  function handleSelectStore(store: StoreDocument) {
    setSelectedStore(store)
    setStoreText(store.name)
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!canSubmit || !selectedStore) return
    setSubmitted({
      // The engine still requires a quantity; the cart total is what actually
      // drives the stack, so we always price a single-line cart.
      params: { storeId: selectedStore.storeId, cartTotal: total, cartQuantity: 1 },
      storeName: selectedStore.name,
    })
  }

  const [winner, ...runnersUp] = data?.results ?? []

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {t("optimizer.optimizeTab.searchWholeMarket")}
        </p>

        <div className="relative">
          {isSearchingStores ? (
            <Loader2 className="pointer-events-none absolute start-4 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
          ) : (
            <Search className="pointer-events-none absolute start-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          )}
          <Input
            type="search"
            value={storeText}
            onChange={(e) => {
              setStoreText(e.target.value)
              if (selectedStore) setSelectedStore(null)
            }}
            placeholder={t("optimizer.optimizeTab.storeNamePlaceholder")}
            autoComplete="off"
            className="h-12 rounded-2xl bg-secondary ps-11"
          />
        </div>

        {selectedStore ? (
          <p className="flex flex-wrap items-center gap-1.5 text-xs text-primary">
            <Check className="size-3.5" aria-hidden />
            {t("optimizer.optimizeTab.pricingAgainst", { store: selectedStore.name })}
            <button
              type="button"
              onClick={() => {
                setSelectedStore(null)
                setStoreText("")
              }}
              className="underline underline-offset-2"
            >
              {t("optimizer.optimizeTab.changeStore")}
            </button>
          </p>
        ) : stores.length > 0 ? (
          <ul className="no-scrollbar max-h-52 space-y-1 overflow-y-auto rounded-2xl border border-border p-1">
            {stores.map((store) => (
              <li key={store.storeId}>
                <button
                  type="button"
                  onClick={() => handleSelectStore(store)}
                  className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-start text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  <Store className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                  {store.name}
                </button>
              </li>
            ))}
          </ul>
        ) : storeText.trim().length >= 2 && !isSearchingStores ? (
          <p className="text-xs text-muted-foreground">
            {t("optimizer.optimizeTab.noStoreMatches", { query: storeText.trim() })}
          </p>
        ) : null}

        <Input
          type="number"
          inputMode="decimal"
          min="0.01"
          step="0.01"
          value={cartTotal}
          onChange={(e) => setCartTotal(e.target.value)}
          placeholder={t("optimizer.optimizeTab.totalPricePlaceholder")}
          className="h-12 rounded-2xl bg-secondary"
        />

        <Button type="submit" variant="hero" size="xl" disabled={!canSubmit || isLoading}>
          {isLoading ? <Loader2 className="animate-spin" /> : <Sparkles />}
          {isLoading ? t("optimizer.optimizeTab.optimizing") : t("optimizer.optimizeTab.findBestPrices")}
        </Button>
        {!canSubmit ? (
          <p className="text-center text-xs text-muted-foreground">{t("optimizer.optimizeTab.requiredNotice")}</p>
        ) : null}
      </form>

      <div className="space-y-3">
        {!submitted ? (
          <Notice>{t("optimizer.optimizeTab.prompt")}</Notice>
        ) : isLoading ? (
          <Notice>{t("optimizer.optimizeTab.optimizing")}</Notice>
        ) : error ? (
          <Notice tone="error">
            {error instanceof Error ? error.message : t("optimizer.optimizeTab.optimizeFailed")}
          </Notice>
        ) : data && !winner ? (
          <Notice>
            {data.deals_considered === 0
              ? t("optimizer.optimizeTab.noDealsAtStore", { store: submitted.storeName })
              : t("optimizer.optimizeTab.noStackApplies", {
                  count: data.deals_considered,
                  store: submitted.storeName,
                })}
          </Notice>
        ) : data && winner ? (
          <>
            <WinningStack result={winner} deals={data.deals} storeName={submitted.storeName} store={data.store} />
            <RankedOptions results={runnersUp} deals={data.deals} store={data.store} />
            <p className="text-center text-xs text-muted-foreground">
              {t("optimizer.optimizeTab.rankedFrom", {
                count: data.deals_considered,
                store: submitted.storeName,
              })}
            </p>
          </>
        ) : null}
      </div>
    </>
  )
}
