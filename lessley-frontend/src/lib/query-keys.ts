export const queryKeys = {
  user: {
    all: ["user"] as const,
    profile: () => [...queryKeys.user.all, "profile"] as const,
    accounts: () => [...queryKeys.user.all, "accounts"] as const,
  },
  transactions: {
    all: ["transactions"] as const,
    list: (days: number) => [...queryKeys.transactions.all, "list", days] as const,
  },
  insights: {
    all: ["insights"] as const,
    categories: (days: number) => [...queryKeys.insights.all, "categories", days] as const,
    topAccounts: (days: number) => [...queryKeys.insights.all, "top-accounts", days] as const,
    topStores: (days: number) => [...queryKeys.insights.all, "top-stores", days] as const,
    spendingByDay: (days: number) => [...queryKeys.insights.all, "spending-by-day", days] as const,
    spendingPeriodComparison: (days: number) =>
      [...queryKeys.insights.all, "spending-period-comparison", days] as const,
    spendingSaved: (days: number) => [...queryKeys.insights.all, "spending-saved", days] as const,
    spendingSavedByAccount: (days: number) =>
      [...queryKeys.insights.all, "spending-saved-by-account", days] as const,
  },
  recommendations: {
    all: ["recommendations"] as const,
    list: () => [...queryKeys.recommendations.all, "list"] as const,
  },
  notifications: {
    all: ["notifications"] as const,
    list: () => [...queryKeys.notifications.all, "list"] as const,
  },
  connection: {
    status: () => ["connection", "status"] as const,
  },
  dealFinder: {
    all: ["dealFinder"] as const,
    categories: () => ["dealFinder", "categories"] as const,
    search: (params: object) => ["dealFinder", "search", params] as const,
    byId: (id: string) => ["dealFinder", "byId", id] as const,
  },
  mcc: {
    categories: () => ["mcc", "categories"] as const,
  },
}
