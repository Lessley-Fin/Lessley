import { useTranslation } from "react-i18next"

export function ConnectionCheck() {
  const { t } = useTranslation()
  return (
    <div className="flex items-center gap-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <span className="size-4 animate-pulse rounded-full bg-primary/50" aria-hidden />
      <p className="text-sm text-muted-foreground">{t("insights.connectionCheck")}</p>
    </div>
  )
}
