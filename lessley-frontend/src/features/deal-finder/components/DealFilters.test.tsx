import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import type { MccCategoryDto } from "@/lib/types"
import { DealFilters } from "./DealFilters"

const mockCategories: MccCategoryDto[] = [
  { category: "GROCERIES" },
  { category: "RESTAURANT" },
  { category: "ELECTRONICS" },
]

describe("DealFilters", () => {
  it("search button is disabled when no filters are set", () => {
    render(<DealFilters onSearch={vi.fn()} mccCategories={mockCategories} />)
    expect(screen.getByRole("button", { name: /search deals/i })).toBeDisabled()
  })

  it("enables search button when store text is entered", async () => {
    const user = userEvent.setup()
    render(<DealFilters onSearch={vi.fn()} mccCategories={mockCategories} />)
    await user.type(screen.getByPlaceholderText(/ksp/i), "pizza")
    expect(screen.getByRole("button", { name: /search deals/i })).toBeEnabled()
  })

  it("enables search button when deal text is entered", async () => {
    const user = userEvent.setup()
    render(<DealFilters onSearch={vi.fn()} mccCategories={mockCategories} />)
    await user.type(screen.getByPlaceholderText(/20% discount/i), "30% off")
    expect(screen.getByRole("button", { name: /search deals/i })).toBeEnabled()
  })

  it("enables search button when a category checkbox is checked", async () => {
    const user = userEvent.setup()
    render(<DealFilters onSearch={vi.fn()} mccCategories={mockCategories} />)
    const groceriesCheckbox = screen.getByRole("checkbox", { name: /groceries/i })
    await user.click(groceriesCheckbox)
    expect(screen.getByRole("button", { name: /search deals/i })).toBeEnabled()
  })

  it("calls onSearch with correct params on button click", async () => {
    const onSearch = vi.fn()
    const user = userEvent.setup()
    render(<DealFilters onSearch={onSearch} mccCategories={mockCategories} />)
    await user.type(screen.getByPlaceholderText(/ksp/i), "pizza hut")
    await user.click(screen.getByRole("button", { name: /search deals/i }))
    expect(onSearch).toHaveBeenCalledWith({
      categories: [],
      storeText: "pizza hut",
      dealText: "",
    })
  })

  it("calls onSearch when Enter is pressed in store input", async () => {
    const onSearch = vi.fn()
    const user = userEvent.setup()
    render(<DealFilters onSearch={onSearch} mccCategories={mockCategories} />)
    await user.type(screen.getByPlaceholderText(/ksp/i), "sushi{Enter}")
    expect(onSearch).toHaveBeenCalledWith({
      categories: [],
      storeText: "sushi",
      dealText: "",
    })
  })

  it("clears all filters when clear button is clicked", async () => {
    const user = userEvent.setup()
    render(<DealFilters onSearch={vi.fn()} mccCategories={mockCategories} />)
    const storeInput = screen.getByPlaceholderText(/ksp/i)
    await user.type(storeInput, "test store")
    await user.click(screen.getByRole("button", { name: /clear/i }))
    expect(storeInput).toHaveValue("")
    expect(screen.getByRole("button", { name: /search deals/i })).toBeDisabled()
  })

  it("shows selected count when categories are checked", async () => {
    const user = userEvent.setup()
    render(<DealFilters onSearch={vi.fn()} mccCategories={mockCategories} />)
    await user.click(screen.getByRole("checkbox", { name: /groceries/i }))
    await user.click(screen.getByRole("checkbox", { name: /restaurant/i }))
    expect(screen.getByText("(2 selected)")).toBeInTheDocument()
  })

  it("includes selected categories in onSearch payload", async () => {
    const onSearch = vi.fn()
    const user = userEvent.setup()
    render(<DealFilters onSearch={onSearch} mccCategories={mockCategories} />)
    await user.click(screen.getByRole("checkbox", { name: /electronics/i }))
    await user.click(screen.getByRole("button", { name: /search deals/i }))
    expect(onSearch).toHaveBeenCalledWith(
      expect.objectContaining({ categories: ["ELECTRONICS"] }),
    )
  })

  it("shows loading message when isLoadingCategories is true", () => {
    render(
      <DealFilters onSearch={vi.fn()} mccCategories={[]} isLoadingCategories={true} />,
    )
    expect(screen.getByText(/loading categories/i)).toBeInTheDocument()
  })

  it("renders category checkboxes from mccCategories prop", () => {
    render(<DealFilters onSearch={vi.fn()} mccCategories={mockCategories} />)
    expect(screen.getByRole("checkbox", { name: /groceries/i })).toBeInTheDocument()
    expect(screen.getByRole("checkbox", { name: /restaurant/i })).toBeInTheDocument()
    expect(screen.getByRole("checkbox", { name: /electronics/i })).toBeInTheDocument()
  })
})
