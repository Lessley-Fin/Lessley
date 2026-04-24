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
