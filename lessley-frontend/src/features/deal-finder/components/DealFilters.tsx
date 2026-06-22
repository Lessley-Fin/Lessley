import { useState } from "react"
import { Search, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MCC_CATEGORIES, formatCategoryLabel } from "@/lib/constants"
import { cn, toggleArrayValue } from "@/lib/utils"
import type { DealSearchFilters } from "../api"

interface DealFiltersProps {
  onSearch: (filters: DealSearchFilters) => void
  isLoading?: boolean
}

export function DealFilters({ onSearch, isLoading }: DealFiltersProps) {
  const [categories, setCategories] = useState<string[]>([])
  const [storeText, setStoreText] = useState("")
  const [dealText, setDealText] = useState("")

  const hasFilter =
    categories.length > 0 || storeText.trim() !== "" || dealText.trim() !== ""

  const handleSearch = () => {
    if (!hasFilter) return
    onSearch({ categories, storeText, dealText })
  }

  const handleClear = () => {
    setCategories([])
    setStoreText("")
    setDealText("")
  }

  return (
    <Card className="fintech-card border-0">
      <CardHeader className="px-4 pb-2 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="fintech-section-title">Find Deals</h2>
          {hasFilter ? (
            <button
              type="button"
              onClick={handleClear}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600"
            >
              <X className="size-3" aria-hidden />
              Clear
            </button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-4 px-4 pb-4">
        <div className="space-y-1.5">
          <Label className="text-sm text-slate-600">Store name</Label>
          <Input
            type="search"
            placeholder="e.g. KSP, McDonald's…"
            value={storeText}
            onChange={(e) => setStoreText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="fintech-input"
          />
        </div>

        <div className="space-y-1.5">
          <Label className="text-sm text-slate-600">Deal description</Label>
          <Input
            type="search"
            placeholder="e.g. 20% discount, free shipping…"
            value={dealText}
            onChange={(e) => setDealText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="fintech-input"
          />
        </div>

        <div className="space-y-1.5">
          <Label className="text-sm text-slate-600">
            Category
            {categories.length > 0 ? (
              <span className="ml-1.5 font-normal text-slate-400">
                ({categories.length} selected)
              </span>
            ) : null}
          </Label>
          <div className="max-h-40 space-y-0.5 overflow-y-auto rounded-2xl border border-slate-100 bg-slate-50/70 p-2">
            {MCC_CATEGORIES.map((cat) => (
              <label
                key={cat}
                className={cn(
                  "flex cursor-pointer select-none items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors",
                  categories.includes(cat)
                    ? "bg-violet-50 text-violet-800"
                    : "text-slate-600 hover:bg-white"
                )}
              >
                <input
                  type="checkbox"
                  className="size-3.5 rounded accent-violet-600"
                  checked={categories.includes(cat)}
                  onChange={() => setCategories(toggleArrayValue(categories, cat))}
                />
                {formatCategoryLabel(cat)}
              </label>
            ))}
          </div>
        </div>

        <Button
          type="button"
          onClick={handleSearch}
          disabled={!hasFilter || isLoading}
          className="w-full rounded-2xl bg-gradient-to-r from-blue-500 to-violet-500 py-3 text-white shadow-md disabled:opacity-50"
        >
          <Search className="mr-2 size-4" aria-hidden />
          {isLoading ? "Searching…" : "Search Deals"}
        </Button>
      </CardContent>
    </Card>
  )
}
