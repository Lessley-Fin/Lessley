import { Landmark } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useHasConnection } from "@/features/insights/hooks"
import { useInitOpenFinance } from "@/features/user/hooks"

export function BankingView() {
  const { data: isConnected } = useHasConnection()
  const initOpenFinance = useInitOpenFinance()

  function handleConnect() {
    initOpenFinance.mutate(undefined, {
      onSuccess: (data) => {
        window.location.assign(data.connectUrl)
      },
    })
  }

  return (
    <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <Landmark className="size-6 text-primary" aria-hidden />
      <p className="font-bold">Connect more cards for sharper insights</p>
      <p className="text-sm text-muted-foreground">
        Each linked card widens the picture of your spending, so club matches and missed-savings alerts get more
        accurate.
      </p>
      <span className="inline-flex w-fit items-center rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold text-secondary-foreground">
        {isConnected ? "Connected" : "Not connected"}
      </span>
      {initOpenFinance.error ? (
        <p className="text-xs text-destructive">Unable to start bank connection. Please try again.</p>
      ) : null}
      <Button type="button" variant="hero" size="xl" onClick={handleConnect} disabled={initOpenFinance.isPending}>
        {initOpenFinance.isPending ? "Connecting..." : isConnected ? "Connect another card" : "Connect a card"}
      </Button>
      <p className="text-center text-xs text-muted-foreground">Read-only access, revocable anytime.</p>
    </div>
  )
}
