import { useState } from "react"
import { Check, Loader2, Search, Store } from "lucide-react"
import { useTranslation } from "react-i18next"

import { DealDetailDialog } from "@/components/shared/DealDetailDialog"
import { DealResultCard } from "@/components/shared/DealResultCard"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useClubs } from "@/features/clubs/hooks"
import type { DealSearchParams } from "@/features/deal-finder/api"
import { useDealSearch, useMccCategories } from "@/features/deal-finder/hooks"
import { formatCategoryLabel } from "@/lib/constants"
import type { DealSearchResultItem, StoreDocument } from "@/lib/types"
import { cn } from "@/lib/utils"
import { useStoreSearch } from "../hooks"

const PAGE_SIZE = 10

export function DealFinderTab() {
  const { t } = useTranslation()
  const [storeText, setStoreText] = useState("")
  const [storeConfirmed, setStoreConfirmed] = useState(false)
  const [dealText, setDealText] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("")
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [submittedParams, setSubmittedParams] = useState<Omit<DealSearchParams, "page" | "pageSize"> | null>(null)
  const [page, setPage] = useState(1)
  const [openItem, setOpenItem] = useState<DealSearchResultItem | null>(null)

  const { data: mccCategories = [] } = useMccCategories()
  const { data: clubs = [] } = useClubs()
  // Confirmed picks skip the query so accepting a suggestion doesn't immediately reopen the list.
  const { data: storeSuggestions = [], isFetching: isSearchingStores } = useStoreSearch(
    storeConfirmed ? "" : storeText
  )

  const enabled = submittedParams !== null
  const queryParams: DealSearchParams = submittedParams
    ? { ...submittedParams, page, pageSize: PAGE_SIZE }
    : { mccCodes: [], storeText: "", dealText: "", page: 1, pageSize: PAGE_SIZE }
  const { data, isLoading, error } = useDealSearch(queryParams, enabled)

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const filteredCategoryChips = mccCategories.filter((mc) =>
    mc.category.toLowerCase().includes(categoryFilter.toLowerCase())
  )

  function handleSearch() {
    setSubmittedParams({ mccCodes: selectedCategories, storeText, dealText })
    setPage(1)
  }

  function toggleCategory(category: string) {
    setSelectedCategories((prev) => (prev.includes(category) ? prev.filter((c) => c !== category) : [...prev, category]))
  }

  function handleSelectStore(store: StoreDocument) {
    setStoreText(store.name)
    setStoreConfirmed(true)
  }

  return (
    <>
      <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
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
              if (storeConfirmed) setStoreConfirmed(false)
            }}
            placeholder={t("dealFinder.tab.storePlaceholder")}
            autoComplete="off"
            className="h-12 rounded-2xl bg-secondary ps-11"
          />
        </div>

        {!storeConfirmed && storeSuggestions.length > 0 ? (
          <ul className="no-scrollbar max-h-52 space-y-1 overflow-y-auto rounded-2xl border border-border p-1">
            {storeSuggestions.map((store) => (
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
        ) : !storeConfirmed && storeText.trim().length >= 2 && !isSearchingStores ? (
          <p className="text-xs text-muted-foreground">
            {t("dealFinder.tab.noStoreMatches", { query: storeText.trim() })}
          </p>
        ) : null}

        <Input
          value={dealText}
          onChange={(e) => setDealText(e.target.value)}
          placeholder={t("dealFinder.tab.dealPlaceholder")}
          className="h-12 rounded-2xl bg-secondary"
        />
        <div>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{t("dealFinder.tab.categoriesLabel")}</p>
          <Input
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            placeholder={t("dealFinder.tab.filterCategoriesPlaceholder", { count: mccCategories.length })}
            className="h-11 rounded-2xl bg-secondary"
          />
          <div className="no-scrollbar mt-3 flex max-h-40 flex-wrap gap-2 overflow-y-auto pe-1">
            {filteredCategoryChips.map((mc) => {
              const isSelected = selectedCategories.includes(mc.category)
              return (
                <button
                  key={mc.category}
                  type="button"
                  onClick={() => toggleCategory(mc.category)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                    isSelected ? "border-primary bg-accent text-accent-foreground" : "border-border bg-card text-muted-foreground"
                  )}
                >
                  {isSelected ? <Check className="me-1 inline size-3" aria-hidden /> : null}
                  {t(`categories.${mc.category}`, { defaultValue: formatCategoryLabel(mc.category) })}
                </button>
              )
            })}
          </div>
        </div>
        <Button type="button" variant="hero" size="xl" onClick={handleSearch}>
          <Search />
          {t("dealFinder.tab.searchDeals")}
        </Button>
      </div>

      <div className="space-y-3">
        {!enabled ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            {t("dealFinder.tab.promptSearch")}
          </p>
        ) : isLoading ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            {t("dealFinder.tab.searching")}
          </p>
        ) : error ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-destructive shadow-[var(--shadow-card)]">
            {error instanceof Error ? error.message : t("dealFinder.hotDeals.loadFailed")}
          </p>
        ) : data && data.items.length === 0 ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            {t("dealFinder.tab.noMatches")}
          </p>
        ) : (
          data?.items.map((item) => <DealResultCard key={item.deal.dealId} item={item} clubs={clubs} onOpen={setOpenItem} />)
        )}

        {totalPages > 1 ? (
          <div className="flex items-center justify-between gap-3 pt-1">
            <Button
              type="button"
              variant="pill"
              size="sm"
              className="rounded-full"
              disabled={page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              {t("dealFinder.tab.previous")}
            </Button>
            <span className="text-sm text-muted-foreground">
              {t("dealFinder.tab.pageOf", { page, total: totalPages })}
            </span>
            <Button
              type="button"
              variant="pill"
              size="sm"
              className="rounded-full"
              disabled={page === totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              {t("dealFinder.tab.next")}
            </Button>
          </div>
        ) : null}
      </div>

      <DealDetailDialog item={openItem} clubs={clubs} onOpenChange={(open) => !open && setOpenItem(null)} />
    </>
  )
}
