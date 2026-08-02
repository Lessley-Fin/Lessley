import { ArrowRight, Landmark } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardTitle } from "@/components/ui/card"
import { fintech } from "@/lib/fintech-styles"

interface ConnectBankCardProps {
  onConnect: () => void
  isPending: boolean
  error: Error | null
}

export function ConnectBankCard({ onConnect, isPending, error }: ConnectBankCardProps) {
  return (
    <Card className="fintech-card overflow-hidden border-0">
      <div className={fintech.gradientBanner}>
        <div className="flex size-10 items-center justify-center rounded-2xl bg-white/20">
          <Landmark className="size-5" />
        </div>
        <CardTitle className="mt-4 text-lg font-semibold text-white">Connect your bank</CardTitle>
        <p className="mt-2 text-sm leading-relaxed text-blue-100">
          Link Open Banking to sync transactions and unlock personalized insights.
        </p>
      </div>
      <CardContent className="space-y-3 px-5 pb-5 pt-4">
        {error ? (
          <p className="text-xs text-amber-700">Unable to start bank connection. Please try again.</p>
        ) : null}
        <Button className="min-h-12 w-full gap-2" onClick={onConnect} disabled={isPending}>
          Connect Open Banking
          <ArrowRight className="size-4" />
        </Button>
        <p className="text-center text-[11px] text-slate-400">
          Regulated Open Banking · Read-only access · You stay in control
        </p>
      </CardContent>
    </Card>
  )
}
