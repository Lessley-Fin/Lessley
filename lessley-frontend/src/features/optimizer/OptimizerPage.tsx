import { useState } from "react"
import { Globe, PackageSearch, Search, Sparkles, Zap } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { fintech } from "@/lib/fintech-styles"

export function OptimizerPage() {
  const [query, setQuery] = useState("")

  return (
    <section className={fintech.page}>
      <Card className="fintech-card overflow-hidden border-0">
        <div className="border-b border-slate-100/80 bg-gradient-to-r from-blue-50 to-violet-50 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className={fintech.iconWrapAmber}>
              <PackageSearch className="size-4" />
            </div>
            <div>
              <CardTitle className="fintech-section-title">Price optimizer</CardTitle>
              <p className="mt-0.5 text-xs text-slate-500">AI-powered deal discovery · Preview</p>
            </div>
          </div>
        </div>
        <CardContent className="space-y-4 px-5 pb-5 pt-4">
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
              className="fintech-input py-3 pl-12 pr-4 text-base"
              aria-label="Product search (preview)"
            />
          </div>
          <Button
            type="button"
            className="min-h-12 w-full gap-2"
            disabled
            aria-disabled="true"
          >
            <Sparkles className="size-4" />
            Find best prices
          </Button>
        </CardContent>
      </Card>

      <Card className="fintech-card border-0">
        <CardHeader className="px-5 pb-2 pt-5">
          <CardTitle className="flex items-center gap-2 fintech-section-title">
            <Zap className="size-4 text-violet-600" />
            What you&apos;ll get
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 px-5 pb-5 pt-0 text-sm text-slate-600">
          <div className="flex gap-3 fintech-card-inset">
            <Sparkles className="mt-0.5 size-4 shrink-0 text-amber-500" />
            <p>Compare offers from multiple stores in one place.</p>
          </div>
          <div className="flex gap-3 fintech-card-inset">
            <PackageSearch className="mt-0.5 size-4 shrink-0 text-blue-600" />
            <p>Spot the lowest price for the exact product you need.</p>
          </div>
          <div className="flex gap-3 fintech-card-inset">
            <Globe className="mt-0.5 size-4 shrink-0 text-emerald-600" />
            <p>We&apos;re building smart matching so results stay relevant.</p>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
