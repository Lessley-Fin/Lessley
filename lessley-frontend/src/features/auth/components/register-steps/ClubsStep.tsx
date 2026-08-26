import type { UseFormReturn } from "react-hook-form"
import { Check } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ClubLogoTile } from "@/components/shared/ClubLogoTile"
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { useClubs } from "@/features/clubs/hooks"
import { cn, toggleArrayValue } from "@/lib/utils"
import type { RegisterValues } from "../../schemas"

interface ClubsStepProps {
  form: UseFormReturn<RegisterValues>
  onContinue: () => void
}

export function ClubsStep({ form, onContinue }: ClubsStepProps) {
  const { t } = useTranslation()
  const { data: clubs = [] } = useClubs()
  const selected = form.watch("clubs") ?? []
  const clubsError = form.formState.errors.clubs?.message

  return (
    <div className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]">
      <div>
        <h1 className="text-xl font-bold">{t("auth.register.clubs.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("auth.register.clubs.subtitle")}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {clubs.map((club) => {
          const isSelected = selected.includes(club.id)
          return (
            <button
              key={club.id}
              type="button"
              onClick={() => {
                form.setValue("clubs", toggleArrayValue(selected, club.id))
                form.clearErrors("clubs")
              }}
              className={cn(
                "flex flex-col items-start gap-2 rounded-2xl border p-4 text-start transition-all",
                isSelected ? "border-primary bg-accent" : "border-border bg-secondary hover:border-primary/40"
              )}
            >
              <ClubLogoTile clubId={club.id} clubName={club.name} />
              <span className="text-sm font-semibold leading-tight">{club.name}</span>
              {isSelected ? (
                <span className="flex items-center gap-1 text-[11px] font-medium text-primary">
                  <Check className="size-3" aria-hidden /> {t("auth.register.clubs.selected")}
                </span>
              ) : null}
            </button>
          )
        })}
      </div>
      <ErrorAlert message={clubsError} />
      <Button type="button" variant="hero" size="xl" onClick={onContinue}>
        {t("common.continue")}
      </Button>
    </div>
  )
}
