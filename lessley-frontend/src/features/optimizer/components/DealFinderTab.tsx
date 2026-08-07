import { useState } from "react"
import { Check, Search } from "lucide-react"

import { DealDetailDialog } from "@/components/shared/DealDetailDialog"
import { DealResultCard } from "@/components/shared/DealResultCard"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useClubs } from "@/features/clubs/hooks"
import type { DealSearchParams } from "@/features/deal-finder/api"
import { useDealSearch, useMccCategories } from "@/features/deal-finder/hooks"
import { formatCategoryLabel } from "@/lib/constants"
import type { DealSearchResultItem } from "@/lib/types"
import { cn } from "@/lib/utils"

const PAGE_SIZE = 10

export function DealFinderTab() {
  const [storeText, setStoreText] = useState("")
  const [dealText, setDealText] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("")
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [submittedParams, setSubmittedParams] = useState<Omit<DealSearchParams, "page" | "pageSize"> | null>(null)
  const [page, setPage] = useState(1)
  const [openItem, setOpenItem] = useState<DealSearchResultItem | null>(null)

  const { data: mccCategories = [] } = useMccCategories()
  const { data: clubs = [] } = useClubs()

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

  return (
    <>
      <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <Input
          value={storeText}
          onChange={(e) => setStoreText(e.target.value)}
          placeholder="Store (optional)"
          className="h-12 rounded-2xl bg-secondary"
        />
        <Input
          value={dealText}
          onChange={(e) => setDealText(e.target.value)}
          placeholder="Find a deal (optional)"
          className="h-12 rounded-2xl bg-secondary"
        />
        <div>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Categories</p>
          <Input
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            placeholder={`Filter ${mccCategories.length} categories`}
            className="h-11 rounded-2xl bg-secondary"
          />
          <div className="no-scrollbar mt-3 flex max-h-40 flex-wrap gap-2 overflow-y-auto pr-1">
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
                  {isSelected ? <Check className="mr-1 inline size-3" aria-hidden /> : null}
                  {formatCategoryLabel(mc.category)}
                </button>
              )
            })}
          </div>
        </div>
        <Button type="button" variant="hero" size="xl" onClick={handleSearch}>
          <Search />
          Search deals
        </Button>
      </div>

      <div className="space-y-3">
        {!enabled ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            Use the filters above to search deals across your loyalty clubs.
          </p>
        ) : isLoading ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            Searching deals…
          </p>
        ) : error ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-destructive shadow-[var(--shadow-card)]">
            {error instanceof Error ? error.message : "Failed to load deals."}
          </p>
        ) : data && data.items.length === 0 ? (
          <p className="rounded-3xl bg-card p-6 text-center text-sm text-muted-foreground shadow-[var(--shadow-card)]">
            No deals match those filters yet 🔍
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
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </span>
            <Button
              type="button"
              variant="pill"
              size="sm"
              className="rounded-full"
              disabled={page === totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
            </Button>
          </div>
        ) : null}
      </div>

      <DealDetailDialog item={openItem} clubs={clubs} onOpenChange={(open) => !open && setOpenItem(null)} />
    </>
  )
}
