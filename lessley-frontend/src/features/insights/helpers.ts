import type { TopStoreInsight } from "@/lib/types"

export function getStoreLabel(store: TopStoreInsight) {
  return store.normalized_merchantName ?? store.merchantName ?? "Unknown store"
}

export function getStoreTransactionCount(store: TopStoreInsight) {
  return store.transaction_count ?? store.total_count ?? 0
}

export function getStoreTotalAmount(store: TopStoreInsight) {
  return store.transaction_amount ?? store.total_amount ?? 0
}
