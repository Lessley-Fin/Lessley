import { useState } from "react"
import { Globe, PackageSearch, Search, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

export function OptimizerPage() {
  const [query, setQuery] = useState("")

  return (
    <section className="space-y-4 px-6 pb-6 pt-4">
      <Card className="overflow-hidden rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
        <CardHeader className="border-b border-slate-100 pb-4 pt-6">
          <div className="flex items-center gap-2">
            <div className="flex size-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
              <PackageSearch className="size-5" />
            </div>
            <div>
              <CardTitle className="text-base">Price optimizer</CardTitle>
              <p className="text-xs text-slate-500">Coming soon</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-5">
          <p className="text-sm leading-relaxed text-slate-600">
            Search for products and we&apos;ll help you find the best prices across the web. This is a preview —
            search is not active yet.
          </p>
          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-slate-400" />
            <Input
              type="search"
              placeholder="What are you looking for?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="min-h-12 rounded-xl border-0 bg-slate-100 py-3 pl-12 pr-4 text-base shadow-none focus-visible:ring-slate-300"
              aria-label="Product search (preview)"
            />
          </div>
          <Button
            type="button"
            className="min-h-12 w-full gap-2 rounded-xl shadow-sm"
            disabled
            aria-disabled="true"
          >
            <Sparkles className="size-4" />
            Find best prices
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-2xl border-0 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
        <CardHeader className="pb-2 pt-5">
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="size-4 text-slate-500" />
            What you&apos;ll get
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-0 text-sm text-slate-600">
          <div className="flex gap-3 rounded-xl bg-slate-50 p-3">
            <Sparkles className="mt-0.5 size-4 shrink-0 text-amber-500" />
            <p>Compare offers from multiple stores in one place.</p>
          </div>
          <div className="flex gap-3 rounded-xl bg-slate-50 p-3">
            <PackageSearch className="mt-0.5 size-4 shrink-0 text-indigo-500" />
            <p>Spot the lowest price for the exact product you need.</p>
          </div>
          <div className="flex gap-3 rounded-xl bg-slate-50 p-3">
            <Globe className="mt-0.5 size-4 shrink-0 text-emerald-600" />
            <p>We&apos;re building smart matching so results stay relevant.</p>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
