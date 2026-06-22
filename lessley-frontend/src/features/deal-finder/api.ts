import { apiFetch } from "@/lib/api-client"
import { MCC_CATEGORY_CODES } from "@/lib/constants"
import type { PagedDealSearchResult } from "@/lib/types"

export interface DealSearchFilters {
  categories: string[]
  storeText: string
  dealText: string
}

export interface DealSearchParams extends DealSearchFilters {
  page: number
  pageSize: number
}

export async function searchDeals(params: DealSearchParams): Promise<PagedDealSearchResult> {
  const mccCodes = params.categories.flatMap((cat) => MCC_CATEGORY_CODES[cat] ?? [])

  const query = new URLSearchParams()
  if (mccCodes.length > 0) query.set("mccs", mccCodes.join(","))
  if (params.storeText.trim()) query.set("store", params.storeText.trim())
  if (params.dealText.trim()) query.set("deal", params.dealText.trim())
  query.set("page", String(params.page))
  query.set("pageSize", String(params.pageSize))

  return apiFetch<PagedDealSearchResult>(`/api/deals/search?${query.toString()}`)
}
