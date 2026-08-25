import { beforeAll, describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import i18n from "@/lib/i18n/config"
import type { MissedShop } from "@/lib/types"
import { MissedShopsSlide } from "./MissedShopsSlide"

// The slide resolves account and club ids against lists it fetches itself. Neither is what
// these tests are about, so stub the hooks rather than standing up a query client — the ids
// below fall through to themselves, which is what the component does with an unknown id anyway.
vi.mock("@/features/insights/hooks", () => ({ useAccounts: () => ({ data: [] }) }))
vi.mock("@/features/clubs/hooks", () => ({
  useClubs: () => ({ data: [{ id: "club_hever_gift_card_company", name: "Hever" }] }),
}))

// The app falls back to Hebrew; pin the language so the assertions are about which strings
// the slide reaches for, not which language it happens to start in.
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

const HEVER = "club_hever_gift_card_company"

function _shop(overrides: Partial<MissedShop> = {}): MissedShop {
  return {
    store_id: "s1",
    store_name: "Steimatzky",
    match_band: "EXACT",
    is_same_store: true,
    deal_count: 1,
    deal_titles: ["Half price"],
    club_ids: [HEVER],
    also_known_as: [],
    covered_transaction_count: 0,
    covered_amount: 0,
    purchases: [],
    ...overrides,
  }
}

const noop = () => {}

function _render(shops: MissedShop[]) {
  render(<MissedShopsSlide shops={shops} isLoading={false} days={30} onDaysChange={noop} />)
}

describe("MissedShopsSlide", () => {
  it("keeps a purchase the club card did not pay for in the missed list", () => {
    _render([
      _shop({
        purchases: [
          { transaction_id: "t1", merchant_name: "Steimatzky", amount: 80, date: null, covered_by_club_ids: [] },
        ],
      }),
    ])

    expect(screen.getByText(/₪80\.00 spent at 1 shop/)).toBeInTheDocument()
    expect(screen.queryByText("Already saved")).not.toBeInTheDocument()
  })

  it("moves a merchant whose every purchase used the club card out of the missed list", () => {
    _render([
      _shop({
        purchases: [
          { transaction_id: "t1", merchant_name: "Steimatzky", amount: 80, date: null, covered_by_club_ids: [HEVER] },
        ],
      }),
    ])

    expect(screen.getByText("Already saved")).toBeInTheDocument()
    expect(screen.getByText(/through Hever/)).toBeInTheDocument()
    expect(
      screen.getByText(/every purchase that matched a deal was paid with your club card/i),
    ).toBeInTheDocument()
  })

  it("counts only the unclaimed half of a merchant the user sometimes used the card at", () => {
    _render([
      _shop({
        purchases: [
          { transaction_id: "t1", merchant_name: "Steimatzky", amount: 80, date: null, covered_by_club_ids: [HEVER] },
          { transaction_id: "t2", merchant_name: "Steimatzky", amount: 20, date: null, covered_by_club_ids: [] },
        ],
      }),
    ])

    // The headline figure is the loss alone — 20, not the 100 that crossed the counter.
    expect(screen.getByText("₪20.00")).toBeInTheDocument()
    expect(screen.getByText(/1 purchase here already saved ₪80\.00 with Hever/)).toBeInTheDocument()
  })

  it("settles a purchase that one lookalike shop still reads as missed", () => {
    // The same coffee matches the shop itself and a café merely like it. The club card paid
    // at the first, so the purchase is claimed — the lookalike must not resurrect it as a loss.
    const paid = { transaction_id: "t1", merchant_name: "Cafe Cafe", amount: 30, date: null }
    _render([
      _shop({ store_id: "s1", store_name: "Cafe Cafe", purchases: [{ ...paid, covered_by_club_ids: [HEVER] }] }),
      _shop({
        store_id: "s2",
        store_name: "Cafe Berlin",
        match_band: "SIMILAR",
        is_same_store: false,
        club_ids: ["c2"],
        purchases: [{ ...paid, covered_by_club_ids: [] }],
      }),
    ])

    expect(screen.getByText("Already saved")).toBeInTheDocument()
    expect(
      screen.getByText(/every purchase that matched a deal was paid with your club card/i),
    ).toBeInTheDocument()
  })

  it("still says nothing matched when nothing matched", () => {
    _render([])

    expect(screen.getByText(/none of your purchases matched a club deal/i)).toBeInTheDocument()
  })

  it("opens on the saved tab when there is nothing left to claim", () => {
    _render([
      _shop({
        purchases: [
          { transaction_id: "t1", merchant_name: "Steimatzky", amount: 80, date: null, covered_by_club_ids: [HEVER] },
        ],
      }),
    ])

    expect(screen.getByRole("button", { name: "Saved (1)" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Your shop (0)" })).toBeDisabled()
    expect(screen.getByText("Already saved")).toBeInTheDocument()
  })

  it("keeps a half-claimed merchant on both tabs, each showing its own money", async () => {
    const user = userEvent.setup()
    _render([
      _shop({
        purchases: [
          { transaction_id: "t1", merchant_name: "Steimatzky", amount: 80, date: null, covered_by_club_ids: [HEVER] },
          { transaction_id: "t2", merchant_name: "Steimatzky", amount: 20, date: null, covered_by_club_ids: [] },
        ],
      }),
    ])

    // The missed tab leads, and leads with the loss alone.
    expect(screen.getByText("Discounts you missed")).toBeInTheDocument()
    expect(screen.getByText(/₪20\.00 spent at 1 shop/)).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Saved (1)" }))

    // The same merchant, the other half of its money, and a header that says so.
    expect(screen.getByText("Already saved")).toBeInTheDocument()
    expect(screen.getByText(/₪80\.00 at 1 shop/)).toBeInTheDocument()
    expect(screen.queryByText("Discounts you missed")).not.toBeInTheDocument()
  })

  it("does not resurrect a settled purchase under a band the settling shop is not in", async () => {
    // The coffee matched the shop itself (EXACT, paid with the club card) and a café merely
    // like it (SIMILAR, which knows nothing about the card). The SIMILAR band is grouped from
    // its own slice of shops, so without a settlement shared across all of them it would show
    // the purchase as a loss the user never took.
    const user = userEvent.setup()
    const paid = { transaction_id: "t1", merchant_name: "Cafe Cafe", amount: 30, date: null }
    _render([
      _shop({ store_id: "s1", store_name: "Cafe Cafe", purchases: [{ ...paid, covered_by_club_ids: [HEVER] }] }),
      _shop({
        store_id: "s2",
        store_name: "Cafe Berlin",
        match_band: "SIMILAR",
        is_same_store: false,
        club_ids: ["c2"],
        purchases: [{ ...paid, covered_by_club_ids: [] }],
      }),
      // Something genuinely missed, so the missed tabs are reachable at all.
      _shop({
        store_id: "s3",
        store_name: "Steimatzky",
        purchases: [
          { transaction_id: "t2", merchant_name: "Steimatzky", amount: 20, date: null, covered_by_club_ids: [] },
        ],
      }),
    ])

    expect(screen.getByRole("button", { name: "Similar shops (0)" })).toBeDisabled()

    await user.click(screen.getByRole("button", { name: "Saved (1)" }))
    expect(screen.getByText(/₪30\.00 at 1 shop/)).toBeInTheDocument()
  })
})
