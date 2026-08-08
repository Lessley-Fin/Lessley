import { Landmark } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { useHasConnection } from "@/features/insights/hooks"
import { useInitOpenFinance } from "@/features/user/hooks"

export function BankingView() {
  const { t } = useTranslation()
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
      <p className="font-bold">{t("settings.banking.title")}</p>
      <p className="text-sm text-muted-foreground">{t("settings.banking.subtitle")}</p>
      <span className="inline-flex w-fit items-center rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold text-secondary-foreground">
        {isConnected ? t("settings.banking.connected") : t("settings.banking.notConnected")}
      </span>
      {initOpenFinance.error ? (
        <p className="text-xs text-destructive">{t("settings.banking.connectError")}</p>
      ) : null}
      <Button type="button" variant="hero" size="xl" onClick={handleConnect} disabled={initOpenFinance.isPending}>
        {initOpenFinance.isPending
          ? t("settings.banking.connecting")
          : isConnected
            ? t("settings.banking.connectAnotherCard")
            : t("settings.banking.connectACard")}
      </Button>
      <p className="text-center text-xs text-muted-foreground">{t("settings.banking.readOnlyNotice")}</p>
    </div>
  )
}
