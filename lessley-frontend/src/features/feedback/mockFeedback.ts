import type { FeedbackItem } from "@/lib/types"

export const initialFeedback: FeedbackItem[] = [
  {
    id: "f-001",
    summary: "Login button is hard to reach on smaller screens.",
    category: "UI",
    createdAt: "Today",
  },
  {
    id: "f-002",
    summary: "Transactions sync appears to freeze after reconnecting a bank.",
    category: "Bug",
    createdAt: "Yesterday",
  },
]
