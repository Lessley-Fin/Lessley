export interface PaginatedApiResponse<T> {
  status: string
  data: T[]
  count: number
  timestamp?: string
}

export interface PersonalizationTransaction {
  id?: string
  userId?: string
  providerId?: string
  accountId?: string
  accountNumber?: string
  status?: string
  categoryCode?: string
  type?: string
  merchantName?: string
  merchantAddress?: {
    country?: string
    townName?: string
  }
  amount?: {
    chargedAmount?: {
      amount?: number
      currency?: string
    }
    originalAmount?: {
      amount?: number
      currency?: string
    }
  }
  description?: {
    description?: string
    fixedText?: string
    initialClean?: string
  }
  category?: {
    categorizedBy?: string
    sub?: string
    main?: string
  }
  date?: {
    transactionDate?: string
    bookingDate?: string
    valueDate?: string
  }
  createdAt?: string
}

export interface SpendingCategoryInsight {
  category: string
  total_count: number
  total_amount: number
}

export interface TopAccountInsight {
  accountId: string
  accountNumber?: string
  providerId?: string
  type?: string
  total_count: number
  total_amount: number
}

export interface ClubRecommendation {
  club_id: string
  club_name: string
  hit_count: number
  total_stores: number
  fit_score: number
  is_recommended: boolean
  is_member: boolean
}

export interface ClubRecommendationResponse {
  email: string
  recommendations: ClubRecommendation[]
}

export interface CalcResult<T = unknown> {
  data: T | null
  calculatedAt: string
}

export interface MissedStore {
  store_id: string
  store_name: string
}

export interface MissedStoreDiscount {
  club_id: string
  missed_store: MissedStore[]
  store_count: number
}

export interface TransactionInsight {
  transaction_id: string
  had_discount: boolean
  store_name: string
  mcc_code: string
  mcc_description: string
  amount: number
  missed_store_discont: MissedStoreDiscount[]
}

export interface RecommendationsResponse {
  missedSavings: CalcResult<TransactionInsight[]> | null
  matchingClubs: CalcResult<ClubRecommendationResponse> | null
}

export interface MccCategoryDto {
  category: string
}

export interface DealDocument {
  dealId: string
  storeId: string
  title: string
  description?: string
  clubId: string
  scrapedAt: string
  resolvedAt?: string
  benefitUrl?: string
  url?: string
  redeemChannels: string[]
  couponCode?: string
}

export interface StoreMetadata {
  mccCodes: string[]
  storeUrl?: string
  imageUrls: string[]
}

export interface StoreDocument {
  storeId: string
  name: string
  metadata: StoreMetadata
}

export interface DealSearchResultItem {
  deal: DealDocument
  store: StoreDocument
}

export interface PagedDealSearchResult {
  items: DealSearchResultItem[]
  total: number
  page: number
  pageSize: number
}

export interface TopStoreInsight {
  normalized_merchantName?: string
  merchantName?: string
  transaction_count?: number
  transaction_amount?: number
  total_count?: number
  total_amount?: number
  spend_by_account?: Array<{
    accountNumber?: string
    transaction_count?: number
    transaction_amount?: number
  }>
}

// ── Deal optimizer ─────────────────────────────────────────────────────────────
// The optimizer service speaks snake_case and the Gateway passes its envelope
// through untouched, so these mirror deal-optimizer's own field names.

/**
 * One rung of a tiered loadable card (e.g. 25% on the first 600 ILS, then 15%
 * up to 1500) and the slice of the bill routed through it.
 */
export interface OptimizerSegment {
  /** 0-based position in the card's ladder. */
  tier_index: number
  /** Savings per ILS at this rung, as a ratio (0.25 === 25%). */
  rate: number
  ils_covered: number
  savings: number
}

/**
 * One deal applied along a path. Fields split into whole-cart running state
 * (`bill_before`/`bill_after`) and this-step-only state (`ils_covered`,
 * `discount_rate`, `savings`) — a card capped at 1000 on a 1200 cart still
 * reports `bill_before: 1200`; `ils_covered` is what that card actually touched.
 */
export interface OptimizerStep {
  deal_id: string
  bill_before: number
  bill_after: number
  /** ILS routed through this payment instrument; null for price-level deals. */
  ils_covered: number | null
  discount_rate: number
  savings: number
  amount_paid_on_covered: number
  /** Bill ILS not yet routed to an instrument; null until the first tender step. */
  remaining_to_allocate: number | null
  cumulative_savings: number
  cumulative_discount_rate: number
  /**
   * Per-rung split of `ils_covered` for a tiered loadable card; null for flat
   * deals. Entries sum to this step's `ils_covered` and `savings`, so
   * `discount_rate` is their blended average rather than any single rung's rate.
   */
  segments: OptimizerSegment[] | null
}

export interface OptimizerResult {
  rank: number
  /** Deal ids in application order — resolve against `deals` for display. */
  path: string[]
  starting_price: number
  final_price: number
  total_savings: number
  per_step: OptimizerStep[]
}

export interface OptimizerDealSummary {
  deal_id: string
  title?: string | null
  description?: string | null
  deal_type?: string | null
  source_id?: string | null
  club_id?: string | null
  url?: string | null
}

export interface OptimizeResponse {
  generated_at: string
  store_id: string
  cart_total: number
  cart_quantity: number
  wallet_id: string | null
  /** Ranked cheapest-first; `results[0]` is the winning stack. */
  results: OptimizerResult[]
  deals: Record<string, OptimizerDealSummary>
  deals_considered: number
}
