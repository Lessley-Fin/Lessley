import { useState } from "react"
import { Sparkles } from "lucide-react"
import { toast } from "sonner"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { formatAmount } from "@/lib/formatters"

const EXAMPLE = {
  store: "KSP",
  listed: 899,
  coupon: 72,
  cashback: 35.96,
}

interface OptimizeResult {
  store: string
  listed: number
}

// There is no backend endpoint for a real stacked-price calculation, so this tab is a clearly
// labeled illustrative demo: it applies fixed 8%/4% example rates to whatever the user enters,
// the same ratios the example card itself uses (72/899 ≈ 8%, 35.96/899 = 4%).
export function OptimizeTab() {
  const { t } = useTranslation()
  const [store, setStore] = useState("")
  const [total, setTotal] = useState("")
  const [result, setResult] = useState<OptimizeResult | null>(null)

  const canSubmit = store.trim().length > 0 && Number(total) > 0

  const listed = result?.listed ?? EXAMPLE.listed
  const coupon = result ? +(listed * 0.08).toFixed(2) : EXAMPLE.coupon
  const cashback = result ? +(listed * 0.04).toFixed(2) : EXAMPLE.cashback
  const finalPrice = +(listed - coupon - cashback).toFixed(2)

  function handleSubmit() {
    setResult({ store: store.trim(), listed: Number(total) })
    toast.success(t("optimizer.optimizeTab.toastSuccess"))
  }

  return (
    <>
      <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {t("optimizer.optimizeTab.searchWholeMarket")}
        </p>
        <Input
          value={store}
          onChange={(e) => setStore(e.target.value)}
          placeholder={t("optimizer.optimizeTab.storeNamePlaceholder")}
          autoComplete="off"
          className="h-12 rounded-2xl bg-secondary"
        />
        <Input
          type="number"
          inputMode="decimal"
          min="0"
          value={total}
          onChange={(e) => setTotal(e.target.value)}
          placeholder={t("optimizer.optimizeTab.totalPricePlaceholder")}
          className="h-12 rounded-2xl bg-secondary"
        />
        <Button type="button" variant="hero" size="xl" disabled={!canSubmit} onClick={handleSubmit}>
          <Sparkles />
          {t("optimizer.optimizeTab.findBestPrices")}
        </Button>
        {!canSubmit ? (
          <p className="text-center text-xs text-muted-foreground">{t("optimizer.optimizeTab.requiredNotice")}</p>
        ) : null}
      </div>

      <div className="rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <p className="mb-3 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {result ? t("optimizer.optimizeTab.result") : t("optimizer.optimizeTab.exampleResult")}
        </p>
        <div className="rounded-2xl border border-dashed border-border p-4">
          <p className="mb-3 font-semibold">{result?.store ?? EXAMPLE.store}</p>
          <ResultRow label={t("optimizer.optimizeTab.listedPrice")} value={formatAmount(listed)} />
          <ResultRow label={t("optimizer.optimizeTab.couponLabel")} value={`−${formatAmount(coupon)}`} accent />
          <ResultRow label={t("optimizer.optimizeTab.cashbackLabel")} value={`−${formatAmount(cashback)}`} accent />
          <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
            <span className="font-semibold">{t("optimizer.optimizeTab.yourPrice")}</span>
            <span className="text-xl font-bold text-primary">{formatAmount(finalPrice)}</span>
          </div>
        </div>
        <p className="mt-3 text-center text-[11px] text-muted-foreground">
          {t("optimizer.optimizeTab.illustrativeNotice")}
        </p>
      </div>
    </>
  )
}

function ResultRow({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={accent ? "font-semibold text-primary" : "font-semibold"}>{value}</span>
    </div>
  )
}
