export type FeedbackCategory = "Bug" | "UI" | "General"

export interface FeedbackItem {
  id: string
  summary: string
  category: FeedbackCategory
  createdAt: string
}

export interface FeedbackSubmission {
  description: string
  category: FeedbackCategory
}

export interface PaginatedApiResponse<T> {
  status: string
  data: T[]
  count: number
}

export interface PersonalizationTransaction {
  id?: string
  merchantName?: string
  accountNumber?: string
  accountId?: string
  categoryCode?: string
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
  is_member?: boolean
}

export interface ClubRecommendationBuckets {
  inAndFit: ClubRecommendation[]
  inNotFit: ClubRecommendation[]
  fitNotIn: ClubRecommendation[]
}

export interface ClubRecommendationResponse {
  user_id: string
  recommendations: ClubRecommendation[]
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
    account_total_count?: number
    account_total_amount?: number
  }>
}
