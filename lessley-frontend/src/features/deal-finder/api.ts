import { apiFetch } from "@/lib/api-client"
import type { DealSearchResultItem, MccCategoryDto, PagedDealSearchResult } from "@/lib/types"

export interface DealSearchFilters {
  categories: string[]
  storeText: string
  dealText: string
}

export interface DealSearchParams {
  mccCodes: string[]
  storeText: string
  dealText: string
  page: number
  pageSize: number
}

export function fetchMccCategories(): Promise<MccCategoryDto[]> {
  return apiFetch<MccCategoryDto[]>("/api/mcc/categories")
}

export function fetchDealById(dealId: string): Promise<DealSearchResultItem> {
  return apiFetch<DealSearchResultItem>(`/api/deals/${encodeURIComponent(dealId)}`)
}

export async function searchDeals(params: DealSearchParams): Promise<PagedDealSearchResult> {
  const query = new URLSearchParams()
  if (params.mccCodes.length > 0) query.set("mccs", params.mccCodes.join(","))
  if (params.storeText.trim()) query.set("store", params.storeText.trim())
  if (params.dealText.trim()) query.set("deal", params.dealText.trim())
  query.set("page", String(params.page))
  query.set("pageSize", String(params.pageSize))

  return apiFetch<PagedDealSearchResult>(`/api/deals/search?${query.toString()}`)
}
