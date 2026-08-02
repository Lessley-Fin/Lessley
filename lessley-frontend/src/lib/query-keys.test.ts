import { describe, it, expect } from "vitest"
import { queryKeys } from "./query-keys"

describe("queryKeys", () => {
  it("generates stable user profile key", () => {
    expect(queryKeys.user.profile()).toEqual(["user", "profile"])
  })

  it("generates transaction keys with days parameter", () => {
    expect(queryKeys.transactions.list(30)).toEqual(["transactions", "list", 30])
    expect(queryKeys.transactions.list(90)).toEqual(["transactions", "list", 90])
  })

  it("generates insight keys with days parameter", () => {
    expect(queryKeys.insights.categories(7)).toEqual(["insights", "categories", 7])
    expect(queryKeys.insights.topAccounts(90)).toEqual(["insights", "top-accounts", 90])
    expect(queryKeys.insights.topStores(365)).toEqual(["insights", "top-stores", 365])
  })

  it("generates notification keys", () => {
    expect(queryKeys.notifications.list()).toEqual(["notifications", "list"])
  })

  it("generates connection status key", () => {
    expect(queryKeys.connection.status()).toEqual(["connection", "status"])
  })

  it("all keys share a common prefix for invalidation", () => {
    const txKeys = queryKeys.transactions.list(30)
    expect(txKeys[0]).toBe(queryKeys.transactions.all[0])
  })
})
