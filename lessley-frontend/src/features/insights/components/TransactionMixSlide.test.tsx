import { beforeAll, describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"

import i18n from "@/lib/i18n/config"
import type { TransactionMixEntry } from "@/lib/types"
import { TransactionMixSlide } from "./TransactionMixSlide"

// The app falls back to Hebrew, so a test that just renders gets Hebrew copy. Pin the language
// rather than inheriting it — the assertions below are about which strings the slide reaches
// for, not about which language the app happens to start in.
beforeAll(async () => {
  await i18n.changeLanguage("en")
})

// The real make-up of one year in local-data/shmer.json. `contributes` is what each part adds
// to the spend total: a refund subtracts, and a coupon adds nothing because no money left the
// account. They come to 40,000 + 8,071.43 + 4,376 - 624.64 + 0 = 51,822.79.
const realYear: TransactionMixEntry[] = [
  { kind: "ordinary", count: 315, amount: 40000.0, contributes: 40000.0 },
  { kind: "foreign", count: 21, amount: 8071.43, contributes: 8071.43, markup_fees: 235.69 },
  { kind: "installment", count: 7, amount: 4376.0, contributes: 4376.0, plan_count: 2 },
  { kind: "refund", count: 7, amount: 624.64, contributes: -624.64 },
  { kind: "coupon", count: 5, amount: 384.6, contributes: 0 },
]

const REAL_YEAR_SPEND = 51822.79

describe("TransactionMixSlide", () => {
  it("names every kind the period contained", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" totalAmount={REAL_YEAR_SPEND} />)

    // Each label appears twice: once in the list, once in the sum below it. Both are wanted.
    for (const label of ["Everyday", "Abroad", "In payments", "Came back", "Coupon"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
    }
  })

  it("writes out the sum, so nobody has to work out why it is not the parts added up", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" totalAmount={REAL_YEAR_SPEND} />)

    // A coupon adds nothing and a credit subtracts — the two things people read as a mistake.
    expect(screen.getByText(/₪0\.00/)).toBeInTheDocument()
    expect(screen.getByText(/₪51,822\.79/)).toBeInTheDocument()
    expect(screen.getByText(/no money left the bank, and a credit subtracts/i)).toBeInTheDocument()
  })

  it("says what the currency conversions cost, not just what was spent abroad", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" totalAmount={REAL_YEAR_SPEND} />)

    expect(screen.getByText(/₪235\.69 of it went on conversion fees/)).toBeInTheDocument()
  })

  it("counts plans rather than repeating the payment count", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" totalAmount={REAL_YEAR_SPEND} />)

    expect(screen.getByText("Payments on 2 plans")).toBeInTheDocument()
  })

  it("tells the user a coupon purchase was money they kept", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" totalAmount={REAL_YEAR_SPEND} />)

    expect(screen.getByText("Money you kept")).toBeInTheDocument()
  })

  it("describes the bar for screen readers, which cannot see proportions", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" totalAmount={REAL_YEAR_SPEND} />)

    expect(screen.getByRole("img")).toHaveAccessibleName(
      "Everyday: 315, Abroad: 21, In payments: 7, Came back: 7, Coupon: 5",
    )
  })

  it("shows only the kinds the period actually contained", () => {
    render(
      <TransactionMixSlide composition={[{ kind: "ordinary", count: 3, amount: 300, contributes: 300 }]} periodLabel="last 90 days" totalAmount={0} />,
    )

    expect(screen.getAllByText("Everyday").length).toBeGreaterThan(0)
    expect(screen.queryByText("Abroad")).not.toBeInTheDocument()
  })

  it("falls back to an empty message rather than an empty bar", () => {
    render(<TransactionMixSlide composition={[]} periodLabel="last 90 days" totalAmount={0} />)

    expect(screen.getByText("No transactions in this period.")).toBeInTheDocument()
    expect(screen.queryByRole("img")).not.toBeInTheDocument()
  })
})
