import { ArrowRight, Landmark } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"

interface ConnectBankCardProps {
  onConnect: () => void
  isPending: boolean
  error: Error | null
}

export function ConnectBankCard({ onConnect, isPending, error }: ConnectBankCardProps) {
  const { t } = useTranslation()
  return (
    <div className="surface-navy space-y-4 rounded-3xl p-6 shadow-[var(--shadow-card)]">
      <div className="flex size-10 items-center justify-center rounded-2xl bg-card/15">
        <Landmark className="size-5" aria-hidden />
      </div>
      <div>
        <p className="text-lg font-bold">{t("insights.connectBank.title")}</p>
        <p className="mt-1 text-sm text-navy-muted">{t("insights.connectBank.subtitle")}</p>
      </div>
      {error ? <p className="text-xs text-warning">{t("insights.connectBank.error")}</p> : null}
      <Button variant="hero" size="xl" onClick={onConnect} disabled={isPending}>
        {t("insights.connectBank.cta")}
        <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
      </Button>
      <p className="text-center text-[11px] text-navy-muted">{t("insights.connectBank.footer")}</p>
    </div>
  )
}
