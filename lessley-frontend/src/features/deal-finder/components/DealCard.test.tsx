import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import type { DealSearchResultItem } from "@/lib/types"
import { DealCard } from "./DealCard"

const baseItem: DealSearchResultItem = {
  deal: {
    dealId: "deal-1",
    storeId: "store-1",
    title: "20% off everything",
    description: "Get 20% off on all items this weekend",
    clubId: "club_hot",
    scrapedAt: "2025-01-15T10:00:00Z",
  },
  store: {
    storeId: "store-1",
    name: "Test Store",
    metadata: {
      mccCodes: [5311],
      storeUrl: "https://test-store.com",
      imageUrls: ["https://example.com/img1.jpg"],
    },
  },
}

describe("DealCard", () => {
  it("renders store name and deal title", () => {
    render(<DealCard item={baseItem} />)
    expect(screen.getByText("Test Store")).toBeInTheDocument()
    expect(screen.getByText("20% off everything")).toBeInTheDocument()
  })

  it("shows club name for known club id", () => {
    render(<DealCard item={baseItem} />)
    expect(screen.getByText("HOT Israel")).toBeInTheDocument()
  })

  it("falls back to raw club id for unknown clubs", () => {
    const item = { ...baseItem, deal: { ...baseItem.deal, clubId: "club_unknown" } }
    render(<DealCard item={item} />)
    expect(screen.getByText("club_unknown")).toBeInTheDocument()
  })

  it("is collapsed by default — description not visible", () => {
    render(<DealCard item={baseItem} />)
    expect(
      screen.queryByText("Get 20% off on all items this weekend"),
    ).not.toBeInTheDocument()
  })

  it("expands on click revealing description", async () => {
    const user = userEvent.setup()
    render(<DealCard item={baseItem} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(screen.getByText("Get 20% off on all items this weekend")).toBeInTheDocument()
  })

  it("shows store URL link when expanded", async () => {
    const user = userEvent.setup()
    render(<DealCard item={baseItem} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(screen.getByRole("link", { name: /visit store/i })).toHaveAttribute(
      "href",
      "https://test-store.com",
    )
  })

  it("collapses again on second click", async () => {
    const user = userEvent.setup()
    render(<DealCard item={baseItem} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    await user.click(screen.getByRole("button", { name: /collapse deal/i }))
    expect(
      screen.queryByText("Get 20% off on all items this weekend"),
    ).not.toBeInTheDocument()
  })

  it("does not render store URL when none is provided", async () => {
    const user = userEvent.setup()
    const item: DealSearchResultItem = {
      ...baseItem,
      store: {
        ...baseItem.store,
        metadata: { ...baseItem.store.metadata, storeUrl: undefined },
      },
    }
    render(<DealCard item={item} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(screen.queryByRole("link", { name: /visit store/i })).not.toBeInTheDocument()
  })

  it("does not render description section when deal has no description", async () => {
    const user = userEvent.setup()
    const item: DealSearchResultItem = {
      ...baseItem,
      deal: { ...baseItem.deal, description: undefined },
    }
    render(<DealCard item={item} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(
      screen.queryByText("Get 20% off on all items this weekend"),
    ).not.toBeInTheDocument()
  })
})
