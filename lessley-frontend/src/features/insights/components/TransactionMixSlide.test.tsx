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

// The real make-up of one year in local-data/shmer.json.
const realYear: TransactionMixEntry[] = [
  { kind: "ordinary", count: 315, amount: 40000.0 },
  { kind: "foreign", count: 21, amount: 8071.43, markup_fees: 235.69 },
  { kind: "installment", count: 7, amount: 4376.0, plan_count: 2 },
  { kind: "refund", count: 7, amount: 624.64 },
  { kind: "voucher", count: 5, amount: 384.6 },
]

describe("TransactionMixSlide", () => {
  it("names every kind the period contained", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" />)

    for (const label of ["Everyday", "Abroad", "In payments", "Came back", "Cost nothing"]) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })

  it("says what the currency conversions cost, not just what was spent abroad", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" />)

    expect(screen.getByText(/₪235\.69 of it went on conversion fees/)).toBeInTheDocument()
  })

  it("counts plans rather than repeating the payment count", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" />)

    expect(screen.getByText("Payments on 2 plans")).toBeInTheDocument()
  })

  it("tells the user a voucher purchase was money they kept", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" />)

    expect(screen.getByText("Money you kept")).toBeInTheDocument()
  })

  it("describes the bar for screen readers, which cannot see proportions", () => {
    render(<TransactionMixSlide composition={realYear} periodLabel="last year" />)

    expect(screen.getByRole("img")).toHaveAccessibleName(
      "Everyday: 315, Abroad: 21, In payments: 7, Came back: 7, Cost nothing: 5",
    )
  })

  it("shows only the kinds the period actually contained", () => {
    render(
      <TransactionMixSlide composition={[{ kind: "ordinary", count: 3, amount: 300 }]} periodLabel="last 90 days" />,
    )

    expect(screen.getByText("Everyday")).toBeInTheDocument()
    expect(screen.queryByText("Abroad")).not.toBeInTheDocument()
  })

  it("falls back to an empty message rather than an empty bar", () => {
    render(<TransactionMixSlide composition={[]} periodLabel="last 90 days" />)

    expect(screen.getByText("No transactions in this period.")).toBeInTheDocument()
    expect(screen.queryByRole("img")).not.toBeInTheDocument()
  })
})
