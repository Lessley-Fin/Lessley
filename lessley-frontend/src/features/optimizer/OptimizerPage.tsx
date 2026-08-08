import { useSearchParams } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import { DealFinderTab } from "./components/DealFinderTab"
import { EngineInfoDialog } from "./components/EngineInfoDialog"
import { OptimizeTab } from "./components/OptimizeTab"

type Tab = "optimize" | "deal-finder"

export function OptimizerPage() {
  const { t } = useTranslation()
  const TABS: { id: Tab; label: string }[] = [
    { id: "optimize", label: t("optimizer.page.tabOptimize") },
    { id: "deal-finder", label: t("optimizer.page.tabDealFinder") },
  ]
  const [searchParams, setSearchParams] = useSearchParams()
  const tab: Tab = searchParams.get("tab") === "deal-finder" ? "deal-finder" : "optimize"

  function setTab(next: Tab) {
    setSearchParams({ tab: next })
  }

  return (
    <div className="space-y-4 pb-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {tab === "optimize" ? t("optimizer.page.priceOptimizerTitle") : t("optimizer.page.dealFinderTitle")}
          </h1>
          <p className="text-sm text-muted-foreground">
            {tab === "optimize" ? t("optimizer.page.priceOptimizerSubtitle") : t("optimizer.page.dealFinderSubtitle")}
          </p>
        </div>
        <EngineInfoDialog />
      </div>

      <div className="flex gap-1 rounded-full border border-border bg-card p-1">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn(
              "flex-1 rounded-full py-2 text-sm font-semibold transition-colors",
              tab === id ? "surface-teal shadow-[var(--shadow-card)]" : "text-muted-foreground"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "optimize" ? <OptimizeTab /> : <DealFinderTab />}
    </div>
  )
}
