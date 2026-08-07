import type { UseFormReturn } from "react-hook-form"
import { Check, Loader2 } from "lucide-react"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import { useClubs } from "@/features/clubs/hooks"
import { emojiForClub } from "@/lib/constants"
import { cn, toggleArrayValue } from "@/lib/utils"
import type { RegisterValues } from "../../schemas"

interface ClubsStepProps {
  form: UseFormReturn<RegisterValues>
  isLoading: boolean
  serverError: string | undefined
  onContinue: () => void
}

export function ClubsStep({ form, isLoading, serverError, onContinue }: ClubsStepProps) {
  const { data: clubs = [] } = useClubs()
  const selected = form.watch("clubs") ?? []

  return (
    <div className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]">
      <div>
        <h1 className="text-xl font-bold">Which clubs do you own? 🎟️</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Optional — pick what you already have and we'll start matching deals right away.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {clubs.map((club) => {
          const isSelected = selected.includes(club.id)
          return (
            <button
              key={club.id}
              type="button"
              disabled={isLoading}
              onClick={() => form.setValue("clubs", toggleArrayValue(selected, club.id))}
              className={cn(
                "flex flex-col items-start gap-2 rounded-2xl border p-4 text-left transition-all",
                isSelected ? "border-primary bg-accent" : "border-border bg-secondary hover:border-primary/40"
              )}
            >
              <span className="text-2xl">{emojiForClub(club.name)}</span>
              <span className="text-sm font-semibold leading-tight">{club.name}</span>
              {isSelected ? (
                <span className="flex items-center gap-1 text-[11px] font-medium text-primary">
                  <Check className="size-3" aria-hidden /> Selected
                </span>
              ) : null}
            </button>
          )
        })}
      </div>
      <ErrorAlert message={serverError} />
      <Button type="button" variant="hero" size="xl" disabled={isLoading} onClick={onContinue}>
        {isLoading ? <Loader2 className="size-4 animate-spin" /> : null}
        {isLoading ? "Creating account..." : "Continue"}
      </Button>
    </div>
  )
}
