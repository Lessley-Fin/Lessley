import { apiFetch, jsonBody } from "@/lib/api-client"
import type { OptimizeResponse, StoreDocument } from "@/lib/types"
import { searchDeals } from "@/features/deal-finder/api"

/** Deals one stack may combine. The engine will chain seven coupons for another
 *  few shekels; nobody juggles seven coupons at a checkout. Mirrors the
 *  optimizer's own default so the two can't drift apart silently. */
export const DEFAULT_MAX_DEALS = 3
/** What the picker offers — one deal (no stacking) up to five. */
export const MAX_DEALS_OPTIONS = [1, 2, 3, 4, 5] as const

export interface OptimizeParams {
  storeId: string
  cartTotal: number
  cartQuantity: number
  topN?: number
  /** Longest combination to search for — the most deals one option may stack. */
  maxDeals?: number
  strict?: boolean
  memberSourceIds?: string[]
}

/**
 * Caddy routes /api/v1/optimizer/* straight to the deal-optimizer service — the Gateway
 * is not in this path — so the body is snake_case, matching that service's own request
 * model (and the snake_case `OptimizeResponse` it already returns).
 */
export function optimizeCart(params: OptimizeParams): Promise<OptimizeResponse> {
  return apiFetch<OptimizeResponse>(
    "/api/v1/optimizer/optimize",
    {
      ...jsonBody({
        store_id: params.storeId,
        cart_total: params.cartTotal,
        cart_quantity: params.cartQuantity,
        top_n: params.topN ?? 5,
        max_deals: params.maxDeals ?? DEFAULT_MAX_DEALS,
        strict: params.strict ?? false,
        member_source_ids: params.memberSourceIds ?? [],
      }),
      errorMessage: "Could not optimize this cart.",
    },
  )
}

/**
 * Resolve a store name fragment to pickable stores. The optimizer keys on
 * store_id, which a user never types — so we reuse the deal-search endpoint
 * and dedupe the stores out of its results rather than adding a second
 * store-lookup endpoint to the Gateway.
 */
export async function searchStores(storeText: string): Promise<StoreDocument[]> {
  const page = await searchDeals({
    mccCodes: [],
    storeText,
    dealText: "",
    page: 1,
    pageSize: 50,
  })

  const byId = new Map<string, StoreDocument>()
  for (const item of page.items) {
    if (!byId.has(item.store.storeId)) byId.set(item.store.storeId, item.store)
  }
  return [...byId.values()]
}
