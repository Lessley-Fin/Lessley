import { Building2, Landmark, Loader2, Lock, ShieldCheck, Sparkles, TrendingUp } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { useInitOpenFinance } from "@/features/user/hooks"

interface BankingStepProps {
  onFinish: () => void
}

export function BankingStep({ onFinish }: BankingStepProps) {
  const { t } = useTranslation()
  const VALUE_PROPS = [
    { icon: Building2, text: t("auth.register.banking.valueProp1") },
    { icon: TrendingUp, text: t("auth.register.banking.valueProp2") },
    { icon: Sparkles, text: t("auth.register.banking.valueProp3") },
  ]
  const initOpenFinance = useInitOpenFinance()

  function handleConnect() {
    initOpenFinance.mutate(undefined, {
      onSuccess: (data) => {
        if (data.connectUrl) window.location.assign(data.connectUrl)
        else onFinish()
      },
    })
  }

  return (
    <div className="space-y-4">
      <div className="surface-navy space-y-4 rounded-3xl p-6 shadow-[var(--shadow-card)]">
        <Landmark className="size-8" aria-hidden />
        <h1 className="text-xl font-bold leading-tight">{t("auth.register.banking.title")}</h1>
        <p className="text-sm text-navy-muted">{t("auth.register.banking.subtitle")}</p>
        <ul className="space-y-2 text-sm">
          {VALUE_PROPS.map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-start gap-2">
              <Icon className="mt-0.5 size-4 shrink-0 text-navy-muted" aria-hidden />
              {text}
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-3 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]">
        <ErrorAlert
          message={initOpenFinance.error instanceof Error ? initOpenFinance.error.message : undefined}
        />
        <Button type="button" variant="hero" size="xl" disabled={initOpenFinance.isPending} onClick={handleConnect}>
          {initOpenFinance.isPending ? <Loader2 className="size-4 animate-spin" /> : <Landmark />}
          {initOpenFinance.isPending ? t("auth.register.banking.connecting") : t("auth.register.banking.connectMyBank")}
        </Button>
        <Button type="button" variant="pill" size="xl" disabled={initOpenFinance.isPending} onClick={onFinish}>
          {t("auth.register.banking.skipForNow")}
        </Button>
        <p className="text-center text-xs text-muted-foreground">{t("auth.register.banking.skipNotice")}</p>
      </div>

      <div className="flex gap-3 rounded-3xl border border-border bg-secondary p-4">
        <Lock className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
        <p className="text-xs leading-relaxed text-muted-foreground">
          {t("auth.register.banking.dataUsageNotice")}
          <ShieldCheck className="ms-1 inline size-3.5 text-primary" aria-hidden />
        </p>
      </div>
    </div>
  )
}
