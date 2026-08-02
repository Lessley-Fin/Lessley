import { useState } from "react"
import { Tag } from "lucide-react"

import { EmptyState } from "@/components/shared/EmptyState"
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { LoadingCard } from "@/components/shared/LoadingCard"
import { fintech } from "@/lib/fintech-styles"
import { DealCard } from "./components/DealCard"
import { DealFilters } from "./components/DealFilters"
import { useDealSearch, useMccCategories } from "./hooks"
import type { DealSearchFilters, DealSearchParams } from "./api"

const PAGE_SIZE = 10

export function DealFinderPage() {
  const [submittedParams, setSubmittedParams] = useState<Omit<DealSearchParams, "page" | "pageSize"> | null>(null)
  const [page, setPage] = useState(1)

  const { data: mccCategories = [], isLoading: isLoadingCategories } = useMccCategories()

  const enabled = submittedParams !== null
  const queryParams: DealSearchParams = submittedParams
    ? { ...submittedParams, page, pageSize: PAGE_SIZE }
    : { mccCodes: [], storeText: "", dealText: "", page: 1, pageSize: PAGE_SIZE }

  const { data, isLoading, error } = useDealSearch(queryParams, enabled)

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  function handleSearch(filters: DealSearchFilters) {
    setSubmittedParams({ mccCodes: filters.categories, storeText: filters.storeText, dealText: filters.dealText })
    setPage(1)
  }

  return (
    <section className={fintech.page}>
      <DealFilters
        onSearch={handleSearch}
        isLoading={isLoading}
        mccCategories={mccCategories}
        isLoadingCategories={isLoadingCategories}
      />

      {!enabled ? (
        <EmptyState
          icon={Tag}
          title="Find your best deals"
          description="Use the filters above to search deals across your loyalty clubs."
        />
      ) : isLoading ? (
        <LoadingCard message="Searching deals…" />
      ) : error ? (
        <ErrorAlert message={error instanceof Error ? error.message : "Failed to load deals."} />
      ) : data && data.items.length === 0 ? (
        <EmptyState
          icon={Tag}
          title="No deals found"
          description="Try adjusting your filters to find more results."
        />
      ) : data ? (
        <>
          <p className={fintech.sectionEyebrow}>
            {data.total} deal{data.total !== 1 ? "s" : ""} found
          </p>

          <div className="space-y-3">
            {data.items.map((item) => (
              <DealCard key={item.deal.dealId} item={item} />
            ))}
          </div>

          {totalPages > 1 ? (
            <div className="flex items-center justify-between gap-3 pt-1">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-slate-500">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
