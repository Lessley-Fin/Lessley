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

export interface RecommendationsResponse {
  missedSavings: CalcResult | null
  matchingClubs: CalcResult<ClubRecommendationResponse> | null
}

export interface MccCategoryDto {
  category: string
  codes: number[]
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
  mccCodes: number[]
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
