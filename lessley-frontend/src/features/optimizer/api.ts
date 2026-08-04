import { apiFetch, jsonBody } from "@/lib/api-client"
import type { OptimizeResponse, StoreDocument } from "@/lib/types"
import { searchDeals } from "@/features/deal-finder/api"

export interface OptimizeParams {
  storeId: string
  cartTotal: number
  cartQuantity: number
  topN?: number
  strict?: boolean
  memberSourceIds?: string[]
}

export function optimizeCart(params: OptimizeParams): Promise<OptimizeResponse> {
  return apiFetch<OptimizeResponse>(
    "/api/optimizer/optimize",
    {
      ...jsonBody({
        storeId: params.storeId,
        cartTotal: params.cartTotal,
        cartQuantity: params.cartQuantity,
        topN: params.topN ?? 5,
        strict: params.strict ?? false,
        memberSourceIds: params.memberSourceIds ?? [],
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
