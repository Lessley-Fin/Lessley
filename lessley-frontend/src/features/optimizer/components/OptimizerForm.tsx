import { useState } from "react"
import { Check, Loader2, Search, Sparkles, Store } from "lucide-react"

import { CardHeaderWithIcon } from "@/components/shared/CardHeaderWithIcon"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import type { StoreDocument } from "@/lib/types"
import { useStoreSearch } from "../hooks"

export interface OptimizerFormValues {
  store: StoreDocument
  cartTotal: number
  cartQuantity: number
}

interface OptimizerFormProps {
  onSubmit: (values: OptimizerFormValues) => void
  isOptimizing: boolean
}

export function OptimizerForm({ onSubmit, isOptimizing }: OptimizerFormProps) {
  const [storeText, setStoreText] = useState("")
  const [selectedStore, setSelectedStore] = useState<StoreDocument | null>(null)
  const [cartTotal, setCartTotal] = useState("")
  const [cartQuantity, setCartQuantity] = useState("1")

  const { data: stores = [], isFetching: isSearchingStores } = useStoreSearch(
    selectedStore ? "" : storeText,
  )

  const total = Number(cartTotal)
  const quantity = Number(cartQuantity)
  const canSubmit =
    selectedStore !== null && Number.isFinite(total) && total > 0 && Number.isFinite(quantity) && quantity >= 1

  function handleSelectStore(store: StoreDocument) {
    setSelectedStore(store)
    setStoreText(store.name)
  }

  function handleClearStore() {
    setSelectedStore(null)
    setStoreText("")
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!canSubmit || !selectedStore) return
    onSubmit({ store: selectedStore, cartTotal: total, cartQuantity: quantity })
  }

  return (
    <Card className="fintech-card border-0">
      <CardHeaderWithIcon
        icon={Sparkles}
        iconColor="amber"
        title="Price optimizer"
        subtitle="Find the cheapest legal stack of deals for your cart"
      />
      <CardContent className="px-5 pb-5 pt-2">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="optimizer-store" className="text-sm font-medium text-slate-700">
              Store
            </label>
            <div className="relative">
              {isSearchingStores ? (
                <Loader2 className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 animate-spin text-slate-400" />
              ) : (
                <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
              )}
              <Input
                id="optimizer-store"
                type="search"
                placeholder="Start typing a store name…"
                value={storeText}
                onChange={(e) => {
                  setStoreText(e.target.value)
                  if (selectedStore) setSelectedStore(null)
                }}
                className="fintech-input pl-11"
                autoComplete="off"
              />
            </div>

            {selectedStore ? (
              <p className="flex items-center gap-2 text-xs text-emerald-700">
                <Check className="size-3.5" />
                Pricing against <span className="font-medium">{selectedStore.name}</span>
                <button
                  type="button"
                  onClick={handleClearStore}
                  className="ml-1 underline underline-offset-2 hover:text-emerald-900"
                >
                  change
                </button>
              </p>
            ) : stores.length > 0 ? (
              <ul className="max-h-52 space-y-1 overflow-y-auto rounded-xl border border-slate-200 p-1">
                {stores.map((store) => (
                  <li key={store.storeId}>
                    <button
                      type="button"
                      onClick={() => handleSelectStore(store)}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    >
                      <Store className="size-3.5 shrink-0 text-slate-400" />
                      {store.name}
                    </button>
                  </li>
                ))}
              </ul>
            ) : storeText.trim().length >= 2 && !isSearchingStores ? (
              <p className="text-xs text-slate-500">No stores matched “{storeText.trim()}”.</p>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label htmlFor="optimizer-total" className="text-sm font-medium text-slate-700">
                Cart total (₪)
              </label>
              <Input
                id="optimizer-total"
                type="number"
                inputMode="decimal"
                min="1"
                step="0.01"
                placeholder="500"
                value={cartTotal}
                onChange={(e) => setCartTotal(e.target.value)}
                className="fintech-input"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="optimizer-quantity" className="text-sm font-medium text-slate-700">
                Items
              </label>
              <Input
                id="optimizer-quantity"
                type="number"
                inputMode="numeric"
                min="1"
                step="1"
                value={cartQuantity}
                onChange={(e) => setCartQuantity(e.target.value)}
                className="fintech-input"
              />
            </div>
          </div>

          <Button type="submit" disabled={!canSubmit || isOptimizing} className={cn("min-h-12 w-full gap-2")}>
            {isOptimizing ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            {isOptimizing ? "Optimizing…" : "Find the best stack"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
