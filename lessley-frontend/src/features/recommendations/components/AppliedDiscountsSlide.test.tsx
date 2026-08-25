import { beforeAll, describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"

import i18n from "@/lib/i18n/config"
import type { AppliedSavings, SavingsMerchant } from "@/lib/types"
import { AppliedDiscountsSlide } from "./AppliedDiscountsSlide"

vi.mock("@/features/insights/hooks", () => ({
  useAccounts: () => ({ data: [{ id: "acc-loaded", product: "נטען", providerId: "isracard" }] }),
}))

beforeAll(async () => {
  await i18n.changeLanguage("en")
})

function _merchant(overrides: Partial<SavingsMerchant> = {}): SavingsMerchant {
  return {
    merchant_name: "Steimatzky",
    band: "",
    purchase_count: 1,
    amount: 80,
    deal_count: 0,
    account_ids: ["acc-loaded"],
    club_ids: [],
    shops: [],
    purchases: [{ transaction_id: "t1", amount: 80, date: null, account_id: "acc-loaded" }],
    ...overrides,
  }
}

function _applied(overrides: Partial<AppliedSavings> = {}): AppliedSavings {
  return { total_amount: 0, purchase_count: 0, merchants: [], ...overrides }
}

const noop = () => {}

function _render(applied: AppliedSavings) {
  render(<AppliedDiscountsSlide applied={applied} isLoading={false} days={30} onDaysChange={noop} />)
}

describe("AppliedDiscountsSlide", () => {
  it("prints the totals it is given, without recomputing them", () => {
    // The header is deliberately inconsistent with the single merchant below it: a component
    // that re-adds the list would print 80 and 1 rather than the service's 1,367 and 12.
    _render(_applied({ total_amount: 1367, purchase_count: 12, merchants: [_merchant()] }))

    expect(screen.getByText(/₪1,367\.00 saved on 12 purchases/)).toBeInTheDocument()
  })

  it("names the card that paid, which is the only part we can name", () => {
    _render(_applied({ total_amount: 80, purchase_count: 1, merchants: [_merchant()] }))

    expect(screen.getByText("Steimatzky")).toBeInTheDocument()
    expect(screen.getByText("₪80.00")).toBeInTheDocument()
    expect(screen.getByText("Paid with נטען · isracard")).toBeInTheDocument()
  })

  it("never claims a club paid, because the feed cannot say which one did", () => {
    // club_ids is empty on every applied merchant by design. Pinned here so no future copy
    // change reaches for it and turns "no money left the account" into a named club.
    _render(_applied({ total_amount: 80, purchase_count: 1, merchants: [_merchant()] }))

    expect(screen.queryByText(/Hever/)).not.toBeInTheDocument()
    expect(screen.queryByText(/through/i)).not.toBeInTheDocument()
  })

  it("says so when no purchase used a club card", () => {
    _render(_applied())

    expect(screen.getByText(/No purchase this period was paid for with a club card/i)).toBeInTheDocument()
  })
})
