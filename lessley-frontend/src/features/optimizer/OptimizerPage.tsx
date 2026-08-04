import { useState } from "react"
import { PackageSearch, Sparkles } from "lucide-react"

import { EmptyState } from "@/components/shared/EmptyState"
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { LoadingCard } from "@/components/shared/LoadingCard"
import { fintech } from "@/lib/fintech-styles"
import { OptimizerForm, type OptimizerFormValues } from "./components/OptimizerForm"
import { RankedOptions } from "./components/RankedOptions"
import { WinningStack } from "./components/WinningStack"
import { useOptimizeCart } from "./hooks"
import type { OptimizeParams } from "./api"

export function OptimizerPage() {
  const [submitted, setSubmitted] = useState<{ params: OptimizeParams; storeName: string } | null>(null)

  const { data, isLoading, error } = useOptimizeCart(submitted?.params ?? null)

  function handleSubmit(values: OptimizerFormValues) {
    setSubmitted({
      params: {
        storeId: values.store.storeId,
        cartTotal: values.cartTotal,
        cartQuantity: values.cartQuantity,
      },
      storeName: values.store.name,
    })
  }

  const [winner, ...runnersUp] = data?.results ?? []

  return (
    <section className={fintech.page}>
      <OptimizerForm onSubmit={handleSubmit} isOptimizing={isLoading} />

      {!submitted ? (
        <EmptyState
          icon={Sparkles}
          title="Price a cart"
          description="Pick a store and enter your cart total — we'll find the cheapest legal combination of deals you can stack."
        />
      ) : isLoading ? (
        <LoadingCard message="Stacking deals…" />
      ) : error ? (
        <ErrorAlert message={error instanceof Error ? error.message : "Failed to optimize this cart."} />
      ) : data && !winner ? (
        <EmptyState
          icon={PackageSearch}
          title="No stack found"
          description={
            data.deals_considered === 0
              ? `We have no deals on file for ${submitted.storeName} yet.`
              : `None of the ${data.deals_considered} deals at ${submitted.storeName} apply to this cart.`
          }
        />
      ) : data && winner ? (
        <>
          <WinningStack result={winner} deals={data.deals} storeName={submitted.storeName} />
          <RankedOptions results={runnersUp} deals={data.deals} />
          <p className="text-center text-xs text-slate-400">
            Ranked from {data.deals_considered} deal{data.deals_considered !== 1 ? "s" : ""} at{" "}
            {submitted.storeName}
          </p>
        </>
      ) : null}
    </section>
  )
}
