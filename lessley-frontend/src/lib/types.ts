export interface PaginatedApiResponse<T> {
  status: string
  data: T[]
  count: number
  timestamp?: string
}

export interface BasicApiResponse<T> {
  status: string
  data: T
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

/**
 * A bank / card account as Open Finance reports it.
 *
 * Insight payloads carry only the account *id*; the readable part of an account — which card
 * it is and who issued it — is read off this list, fetched once and shared by every screen
 * that has to name where a purchase came from.
 */
export interface OpenFinanceAccount {
  id: string
  providerId?: string
  product?: string
  accountNumber?: string
  type?: string
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



/**
 * How sure we are that a shop is the one the user actually visited.
 *
 * The wording on screen has to follow this. EXACT and STRONG mean the name identifies the
 * shop, so "you missed a coupon here" is true. SIMILAR means the names only share a word
 * naming a line of business — "קפה ברלין" against "קפה קפה" — so it is somewhere *like*
 * theirs, and claiming they shopped there would be a lie.
 */
export type StoreMatchBand = "EXACT" | "STRONG" | "SIMILAR"

export interface MissedShopPurchase {
  transaction_id: string
  merchant_name: string
  amount: number
  date: string | null
  /** Which account paid for it — resolve against {@link OpenFinanceAccount} to name it. */
  account_id?: string | null
}

export interface MissedShop {
  store_id: string
  store_name: string
  match_band: StoreMatchBand
  is_same_store: boolean
  deal_count: number
  deal_titles: string[]
  club_ids: string[]
  also_known_as: string[]
  covered_transaction_count: number
  covered_amount: number
  purchases: MissedShopPurchase[]
}

export interface MccCategoryDto {
  category: string
}

export interface ClubDto {
  id: string
  name: string
  /** The scraper id deals are tagged with (`hot`, `mastercard`) — join deals on this. */
  sourceId?: string | null
}

/**
 * What a deal is worth. The pipeline splits the raw discount logic by reward
 * type, so at most one value field is set: `percentOff` is a ratio (0.3 = 30%
 * off), `amountOff` is ILS taken off, `fixedPrice` is a price paid instead.
 */
export interface DealDiscount {
  rewardType?: string | null
  percentOff?: number | null
  amountOff?: number | null
  fixedPrice?: number | null
  maxDiscountAmount?: number | null
  conditionType?: string | null
  minSpend?: number | null
  minQuantity?: number | null
}

export interface DealLimits {
  minimumPurchase?: number | null
  maxUsesPerTransaction?: number | null
  maxUsesPerMonth?: number | null
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
  dealType?: string | null
  currency?: string | null
  termsAndConditions?: string | null
  discount?: DealDiscount | null
  limits?: DealLimits | null
  membershipRequired?: boolean | null
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

export interface SpendingByDayInsight {
  day: string
  total_amount: number
}

export interface SpendingPeriodComparison {
  current_period_total: number
  previous_period_total: number
  difference: number
}

/** One kind of thing that happened in the period. Every countable transaction carries exactly
 *  one kind, so the counts sum to the transaction total and can be drawn as a proportional bar. */
export interface TransactionMixEntry {
  kind: "ordinary" | "foreign" | "installment" | "refund" | "voucher"
  count: number
  /** What was bought, or for a refund, what came back. */
  amount: number
  /** foreign only — what the currency conversions cost in issuer markup. */
  markup_fees?: number
  /** installment only — how many distinct plans these payments belong to. */
  plan_count?: number
}

export interface SpendingTotalInsight {
  /** Money that left the account, less money that came back. Excludes vouchers, which cost
   *  nothing — so this is deliberately smaller than the sum of the per-category breakdowns. */
  total_amount: number
  purchase_count: number
  composition: TransactionMixEntry[]
}

export interface SpendingSavedInsight {
  total_saved: number
}

export interface SpendingSavedByAccountInsight {
  accountId: string
  accountNumber?: string
  total_saved: number
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
  /** Where the benefit is claimed (benefit_url, falling back to the merchant site). */
  url?: string | null
  /** The merchant's own site, when the deal also carries a claim link. */
  store_url?: string | null
  terms_and_conditions?: string | null
  minimum_purchase?: number | null
  max_uses_per_transaction?: number | null
  max_uses_per_month?: number | null
  max_discount_amount?: number | null
  /** Tri-state on the wire: true / "yes" / null. */
  membership_required?: boolean | string | null
}

/**
 * The store a cart was priced at. Snake_case because the Gateway passes the
 * optimizer's own payload through untouched. Deals carry no imagery of their
 * own — the pipeline hangs scraped images off the store.
 */
export interface OptimizerStore {
  store_id: string
  name?: string | null
  store_url?: string | null
  image_urls: string[]
  mcc_codes: string[]
}

export interface OptimizeResponse {
  generated_at: string
  store_id: string
  cart_total: number
  cart_quantity: number
  wallet_id: string | null
  store?: OptimizerStore | null
  /** Ranked cheapest-first; `results[0]` is the winning stack. */
  results: OptimizerResult[]
  deals: Record<string, OptimizerDealSummary>
  deals_considered: number
}
