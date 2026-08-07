import { useState } from "react"
import { Sparkles } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { formatAmount } from "@/lib/formatters"

const EXAMPLE = {
  store: "KSP",
  listed: 899,
  coupon: 72,
  cashback: 35.96,
  couponLabel: "Club coupon (Behatsdaa)",
  cashbackLabel: "Card cashback (Mastercard)",
}

interface OptimizeResult {
  store: string
  listed: number
}

// There is no backend endpoint for a real stacked-price calculation, so this tab is a clearly
// labeled illustrative demo: it applies fixed 8%/4% example rates to whatever the user enters,
// the same ratios the example card itself uses (72/899 ≈ 8%, 35.96/899 = 4%).
export function OptimizeTab() {
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
    toast.success("Best stacked price found 🎉")
  }

  return (
    <>
      <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          Search the whole market
        </p>
        <Input
          value={store}
          onChange={(e) => setStore(e.target.value)}
          placeholder="Store name"
          autoComplete="off"
          className="h-12 rounded-2xl bg-secondary"
        />
        <Input
          type="number"
          inputMode="decimal"
          min="0"
          value={total}
          onChange={(e) => setTotal(e.target.value)}
          placeholder="Total price ₪"
          className="h-12 rounded-2xl bg-secondary"
        />
        <Button type="button" variant="hero" size="xl" disabled={!canSubmit} onClick={handleSubmit}>
          <Sparkles />
          Find best prices
        </Button>
        {!canSubmit ? <p className="text-center text-xs text-muted-foreground">Store and total are required.</p> : null}
      </div>

      <div className="rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
        <p className="mb-3 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          {result ? "Result" : "Example result"}
        </p>
        <div className="rounded-2xl border border-dashed border-border p-4">
          <p className="mb-3 font-semibold">{result?.store ?? EXAMPLE.store}</p>
          <ResultRow label="Listed price" value={formatAmount(listed)} />
          <ResultRow label={EXAMPLE.couponLabel} value={`−${formatAmount(coupon)}`} accent />
          <ResultRow label={EXAMPLE.cashbackLabel} value={`−${formatAmount(cashback)}`} accent />
          <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
            <span className="font-semibold">Your price</span>
            <span className="text-xl font-bold text-primary">{formatAmount(finalPrice)}</span>
          </div>
        </div>
        <p className="mt-3 text-center text-[11px] text-muted-foreground">
          Illustrative estimate — not a live market quote.
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
