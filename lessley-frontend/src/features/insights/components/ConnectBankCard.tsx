import { ArrowRight, Landmark } from "lucide-react"

import { Button } from "@/components/ui/button"

interface ConnectBankCardProps {
  onConnect: () => void
  isPending: boolean
  error: Error | null
}

export function ConnectBankCard({ onConnect, isPending, error }: ConnectBankCardProps) {
  return (
    <div className="surface-navy space-y-4 rounded-3xl p-6 shadow-[var(--shadow-card)]">
      <div className="flex size-10 items-center justify-center rounded-2xl bg-card/15">
        <Landmark className="size-5" aria-hidden />
      </div>
      <div>
        <p className="text-lg font-bold">Connect your bank</p>
        <p className="mt-1 text-sm text-navy-muted">
          Link Open Banking to sync transactions and unlock personalized insights.
        </p>
      </div>
      {error ? <p className="text-xs text-warning">Unable to start bank connection. Please try again.</p> : null}
      <Button variant="hero" size="xl" onClick={onConnect} disabled={isPending}>
        Connect Open Banking
        <ArrowRight className="size-4" aria-hidden />
      </Button>
      <p className="text-center text-[11px] text-navy-muted">
        Regulated Open Banking · Read-only access · You stay in control
      </p>
    </div>
  )
}
