import type { UseFormReturn } from "react-hook-form"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { MATCH_LEVEL_OPTIONS } from "@/lib/constants"
import { cn } from "@/lib/utils"
import type { RegisterValues } from "../../schemas"
import { MatchLevelInfoDialog } from "./MatchLevelInfoDialog"

interface MatchLevelStepProps {
  form: UseFormReturn<RegisterValues>
  isLoading: boolean
  serverError: string | undefined
  onContinue: () => void
}

export function MatchLevelStep({ form, isLoading, serverError, onContinue }: MatchLevelStepProps) {
  const { t } = useTranslation()
  const selected = form.watch("matchLevel")

  return (
    <div className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold">{t("auth.register.matchLevel.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("auth.register.matchLevel.subtitle")}</p>
        </div>
        <MatchLevelInfoDialog />
      </div>
      <div className="space-y-3">
        {MATCH_LEVEL_OPTIONS.map((opt) => {
          const isSelected = selected === opt.value
          return (
            <button
              key={opt.value}
              type="button"
              disabled={isLoading}
              onClick={() => form.setValue("matchLevel", opt.value)}
              className={cn(
                "flex w-full flex-col items-start gap-1 rounded-2xl border p-4 text-start transition-all",
                isSelected ? "border-primary bg-accent" : "border-border bg-secondary hover:border-primary/40"
              )}
            >
              <span className="text-sm font-semibold">{t(`matchLevels.${opt.value}`)}</span>
              <span className="text-xs text-muted-foreground">
                {t(`auth.register.matchLevel.options.${opt.value}`)}
              </span>
            </button>
          )
        })}
      </div>
      <ErrorAlert message={serverError} />
      <Button type="button" variant="hero" size="xl" disabled={isLoading} onClick={onContinue}>
        {isLoading ? <Loader2 className="size-4 animate-spin" /> : null}
        {isLoading ? t("auth.register.creatingAccount") : t("common.continue")}
      </Button>
    </div>
  )
}
