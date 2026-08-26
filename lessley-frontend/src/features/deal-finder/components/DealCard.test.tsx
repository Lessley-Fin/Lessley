import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import type { ClubDto, DealSearchResultItem } from "@/lib/types"
import { DealCard } from "./DealCard"

const mockClubs: ClubDto[] = [
  { id: "club_hot", name: "HOT Israel" },
  // The clubs collection holds only the un-suffixed parent; deals carry the rungs.
  { id: "club_paisplus_networks", name: "PaisPlus — Networks Cash Card" },
]

const baseItem: DealSearchResultItem = {
  deal: {
    dealId: "deal-1",
    storeId: "store-1",
    title: "20% off everything",
    description: "Get 20% off on all items this weekend",
    clubId: "club_hot",
    scrapedAt: "2025-01-15T10:00:00Z",
    redeemChannels: [],
  },
  store: {
    storeId: "store-1",
    name: "Test Store",
    metadata: {
      mccCodes: ["SHOPPING_OTHER"],
      storeUrl: "https://test-store.com",
      imageUrls: ["https://example.com/img1.jpg"],
    },
  },
}

describe("DealCard", () => {
  it("renders store name and deal title", () => {
    render(<DealCard item={baseItem} clubs={mockClubs} />)
    expect(screen.getByText("Test Store")).toBeInTheDocument()
    expect(screen.getByText("20% off everything")).toBeInTheDocument()
  })

  it("shows club name for known club id", () => {
    render(<DealCard item={baseItem} clubs={mockClubs} />)
    expect(screen.getByText("HOT Israel")).toBeInTheDocument()
  })

  it("falls back to raw club id for unknown clubs", () => {
    const item = { ...baseItem, deal: { ...baseItem.deal, clubId: "club_unknown" } }
    render(<DealCard item={item} clubs={mockClubs} />)
    expect(screen.getByText("club_unknown")).toBeInTheDocument()
  })

  it("names a tiered card by its parent club rather than printing the raw rung", () => {
    // A tiered card has no club record of its own, so an exact-id lookup printed
    // `club_paisplus_networks_regular` on the badge.
    const item = {
      ...baseItem,
      deal: { ...baseItem.deal, clubId: "club_paisplus_networks_regular" },
    }
    render(<DealCard item={item} clubs={mockClubs} />)

    expect(screen.getByText("PaisPlus — Networks Cash Card")).toBeInTheDocument()
    expect(screen.queryByText("club_paisplus_networks_regular")).not.toBeInTheDocument()
  })

  it("shows the club artwork next to the name, and both rungs share it", () => {
    const { container, unmount } = render(<DealCard item={baseItem} clubs={mockClubs} />)
    expect(container.querySelector("img[aria-hidden]")).toBeInTheDocument()
    unmount()

    const tiered = {
      ...baseItem,
      deal: { ...baseItem.deal, clubId: "club_paisplus_networks_vip" },
    }
    const { container: tieredContainer } = render(<DealCard item={tiered} clubs={mockClubs} />)
    expect(tieredContainer.querySelector("img[aria-hidden]")).toBeInTheDocument()
  })

  it("is collapsed by default — description not visible", () => {
    render(<DealCard item={baseItem} clubs={mockClubs} />)
    expect(
      screen.queryByText("Get 20% off on all items this weekend"),
    ).not.toBeInTheDocument()
  })

  it("expands on click revealing description", async () => {
    const user = userEvent.setup()
    render(<DealCard item={baseItem} clubs={mockClubs} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(screen.getByText("Get 20% off on all items this weekend")).toBeInTheDocument()
  })

  it("shows store URL link when expanded", async () => {
    const user = userEvent.setup()
    render(<DealCard item={baseItem} clubs={mockClubs} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(screen.getByRole("link", { name: /visit store/i })).toHaveAttribute(
      "href",
      "https://test-store.com",
    )
  })

  it("collapses again on second click", async () => {
    const user = userEvent.setup()
    render(<DealCard item={baseItem} clubs={mockClubs} />)
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
    render(<DealCard item={item} clubs={mockClubs} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(screen.queryByRole("link", { name: /visit store/i })).not.toBeInTheDocument()
  })

  it("does not render description section when deal has no description", async () => {
    const user = userEvent.setup()
    const item: DealSearchResultItem = {
      ...baseItem,
      deal: { ...baseItem.deal, description: undefined },
    }
    render(<DealCard item={item} clubs={mockClubs} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(
      screen.queryByText("Get 20% off on all items this weekend"),
    ).not.toBeInTheDocument()
  })

  it("shows Get Deal link in collapsed view when benefitUrl is present", () => {
    const item: DealSearchResultItem = {
      ...baseItem,
      deal: { ...baseItem.deal, benefitUrl: "https://deal.example.com/buy/123" },
    }
    render(<DealCard item={item} clubs={mockClubs} />)
    const link = screen.getByRole("link", { name: /get deal/i })
    expect(link).toHaveAttribute("href", "https://deal.example.com/buy/123")
    expect(link).toHaveAttribute("target", "_blank")
  })

  it("does not show Get Deal link when benefitUrl is absent", () => {
    render(<DealCard item={baseItem} clubs={mockClubs} />)
    expect(screen.queryByRole("link", { name: /get deal/i })).not.toBeInTheDocument()
  })

  it("shows prominent Get Deal CTA in expanded view when benefitUrl is present", async () => {
    const user = userEvent.setup()
    const item: DealSearchResultItem = {
      ...baseItem,
      deal: { ...baseItem.deal, benefitUrl: "https://deal.example.com/buy/123" },
    }
    render(<DealCard item={item} clubs={mockClubs} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    const links = screen.getAllByRole("link", { name: /get deal/i })
    expect(links.length).toBeGreaterThanOrEqual(1)
    expect(links[0]).toHaveAttribute("href", "https://deal.example.com/buy/123")
  })

  it("shows redeem channel badges in collapsed view", () => {
    const item: DealSearchResultItem = {
      ...baseItem,
      deal: { ...baseItem.deal, redeemChannels: ["online", "physical_store"] },
    }
    render(<DealCard item={item} clubs={mockClubs} />)
    expect(screen.getByText("online")).toBeInTheDocument()
    expect(screen.getByText("physical store")).toBeInTheDocument()
  })

  it("shows coupon code when present in expanded view", async () => {
    const user = userEvent.setup()
    const item: DealSearchResultItem = {
      ...baseItem,
      deal: { ...baseItem.deal, couponCode: "SAVE20" },
    }
    render(<DealCard item={item} clubs={mockClubs} />)
    await user.click(screen.getByRole("button", { name: /expand deal/i }))
    expect(screen.getByText("SAVE20")).toBeInTheDocument()
  })
})
