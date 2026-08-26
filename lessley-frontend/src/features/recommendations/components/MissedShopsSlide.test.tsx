import { beforeAll, describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import i18n from "@/lib/i18n/config"
import type { MissedSavings, SavingsMerchant, StoreMatchBand } from "@/lib/types"
import { MissedShopsSlide } from "./MissedShopsSlide"

vi.mock("@/features/insights/hooks", () => ({ useAccounts: () => ({ data: [] }) }))
vi.mock("@/features/clubs/hooks", () => ({
  useClubs: () => ({ data: [{ id: "club_hever_gift_card_company", name: "Hever" }] }),
}))

beforeAll(async () => {
  await i18n.changeLanguage("en")

  // jsdom has none of matchMedia, IntersectionObserver or ResizeObserver, and the band
  // carousel reaches for all three the moment it mounts. Nothing here is about breakpoints,
  // visibility or size — these stubs only let it finish mounting so the copy can be read.
  window.matchMedia ??= ((query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList) as typeof window.matchMedia

  window.IntersectionObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return []
    }
    readonly root = null
    readonly rootMargin = ""
    readonly thresholds: readonly number[] = []
  } as unknown as typeof window.IntersectionObserver

  window.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof window.ResizeObserver
})

function _merchant(overrides: Partial<SavingsMerchant> = {}): SavingsMerchant {
  return {
    merchant_name: "Steimatzky",
    band: "EXACT",
    purchase_count: 1,
    amount: 80,
    deal_count: 1,
    account_ids: [],
    club_ids: ["club_hever_gift_card_company"],
    sources: [],
    shops: [
      {
        store_id: "s1",
        store_name: "Steimatzky",
        match_band: "EXACT",
        is_same_store: true,
        deal_count: 1,
        deal_titles: ["Half price"],
        club_ids: ["club_hever_gift_card_company"],
        also_known_as: [],
      },
    ],
    purchases: [{ transaction_id: "t1", amount: 80, date: null }],
    ...overrides,
  }
}

function _missed(overrides: Partial<MissedSavings> = {}): MissedSavings {
  return { total_amount: 0, purchase_count: 0, bands: [], ...overrides }
}

const _band = (band: StoreMatchBand, merchants: SavingsMerchant[], total: number, count: number) => ({
  band,
  total_amount: total,
  purchase_count: count,
  merchants,
})

const noop = () => {}

function _render(missed: MissedSavings) {
  render(<MissedShopsSlide missed={missed} isLoading={false} days={30} onDaysChange={noop} />)
}

describe("MissedShopsSlide", () => {
  it("prints the totals it is given, without recomputing them", () => {
    // The header total and the tab count are deliberately inconsistent with the merchants
    // below them. A component that renders what the service said will show the service's
    // figures; one that quietly re-adds the merchants will show 80 and 1 instead. That
    // re-adding is exactly what used to make the screen disagree with the service.
    _render(
      _missed({
        total_amount: 4470.87,
        purchase_count: 33,
        bands: [_band("EXACT", [_merchant()], 271, 4)],
      }),
    )

    expect(screen.getByText(/₪4,470\.87 on 33 purchases/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Your shop (4)" })).toBeInTheDocument()
  })

  it("shows one tab per band the service returned, and no others", () => {
    _render(
      _missed({
        total_amount: 100,
        purchase_count: 2,
        bands: [
          _band("EXACT", [_merchant()], 80, 1),
          _band("SIMILAR", [_merchant({ merchant_name: "Cafe Berlin", band: "SIMILAR", amount: 20 })], 20, 1),
        ],
      }),
    )

    expect(screen.getByRole("button", { name: "Your shop (1)" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Similar shops (1)" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Probably yours/ })).not.toBeInTheDocument()
  })

  it("opens on the first band and switches on click", async () => {
    const user = userEvent.setup()
    _render(
      _missed({
        total_amount: 100,
        purchase_count: 2,
        bands: [
          _band("EXACT", [_merchant()], 80, 1),
          _band("SIMILAR", [_merchant({ merchant_name: "Cafe Berlin", band: "SIMILAR", amount: 20 })], 20, 1),
        ],
      }),
    )

    expect(screen.getByText("The same shop you paid at, matched by name.")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Similar shops (1)" }))

    expect(screen.getByText("Cafe Berlin")).toBeInTheDocument()
    expect(
      screen.getByText("Not your shop — somewhere that sells the same sort of thing."),
    ).toBeInTheDocument()
  })

  it("says nothing matched when the service returned no bands", () => {
    _render(_missed())

    expect(screen.getByText(/none of your purchases matched a club deal/i)).toBeInTheDocument()
  })

  it("names the club off the shop, and the merchant's own amount", () => {
    _render(
      _missed({
        total_amount: 80,
        purchase_count: 1,
        bands: [_band("EXACT", [_merchant()], 80, 1)],
      }),
    )

    expect(screen.getByText("₪80.00")).toBeInTheDocument()
    expect(screen.getByText("Yours through Hever")).toBeInTheDocument()
  })
})
