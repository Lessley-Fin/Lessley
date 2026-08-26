import { useState } from "react"
import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"

import { ClubLogoTile } from "@/components/shared/ClubLogoTile"
import { Button } from "@/components/ui/button"
import { useClubs } from "@/features/clubs/hooks"
import type { MeResponse } from "@/features/user/api"
import { useUpdateMyProfile } from "@/features/user/hooks"
import { MATCH_LEVEL_OPTIONS, formatCategoryLabel } from "@/lib/constants"
import { cn, toggleArrayValue } from "@/lib/utils"

interface ChipProps {
  active: boolean
  onClick: () => void
  /** Artwork shown before the label. Tightens the leading padding so the plate
      sits flush inside the pill instead of floating in text-sized padding. */
  leading?: ReactNode
  children: ReactNode
}

function Chip({ active, onClick, leading, children }: ChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border py-1.5 text-xs font-medium transition-colors",
        leading ? "ps-1.5 pe-3" : "px-3",
        active ? "border-primary bg-accent text-accent-foreground" : "border-border bg-card text-muted-foreground",
      )}
    >
      {leading}
      {children}
    </button>
  )
}

interface PreferencesViewProps {
  profile: MeResponse
}

export function PreferencesView({ profile }: PreferencesViewProps) {
  const { t } = useTranslation()
  const { data: clubs = [] } = useClubs()
  const updateProfile = useUpdateMyProfile()

  const [selectedClubs, setSelectedClubs] = useState<string[]>(profile.clubs)
  const [matchLevel, setMatchLevel] = useState<"Low" | "Medium" | "High" | null>(profile.matchLevel)
  const [mutedTags, setMutedTags] = useState<string[]>(profile.mutedTags)

  function handleSave() {
    updateProfile.mutate({ clubs: selectedClubs, matchLevel, mutedTags })
  }

  return (
    <div className="space-y-4 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <div>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{t("settings.preferences.loyaltyClubs")}</p>
        <div className="flex flex-wrap gap-2">
          {clubs.map((club) => (
            <Chip
              key={club.id}
              active={selectedClubs.includes(club.id)}
              onClick={() => setSelectedClubs((prev) => toggleArrayValue(prev, club.id))}
              leading={<ClubLogoTile clubId={club.id} clubName={club.name} variant="inline" />}
            >
              {club.name}
            </Chip>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{t("settings.preferences.matchLevel")}</p>
        <div className="flex flex-wrap gap-2">
          {MATCH_LEVEL_OPTIONS.map((opt) => (
            <Chip key={opt.value} active={matchLevel === opt.value} onClick={() => setMatchLevel(opt.value)}>
              {t(`matchLevels.${opt.value}`)}
            </Chip>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{t("settings.preferences.mutedCategories")}</p>
        {profile.tags.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("settings.preferences.noTagsYet")}</p>
        ) : (
          <div className="no-scrollbar flex max-h-44 flex-wrap gap-2 overflow-y-auto pe-1">
            {profile.tags.map((tag) => (
              <Chip
                key={tag}
                active={mutedTags.includes(tag)}
                onClick={() => setMutedTags((prev) => toggleArrayValue(prev, tag))}
              >
                {t(`categories.${tag}`, { defaultValue: formatCategoryLabel(tag) })}
              </Chip>
            ))}
          </div>
        )}
      </div>

      {updateProfile.error ? (
        <p className="text-xs text-destructive">
          {updateProfile.error instanceof Error ? updateProfile.error.message : t("settings.preferences.saveFailed")}
        </p>
      ) : null}
      {updateProfile.isSuccess ? <p className="text-xs text-success">{t("settings.preferences.saved")}</p> : null}

      <Button type="button" variant="hero" size="xl" onClick={handleSave} disabled={updateProfile.isPending}>
        {updateProfile.isPending ? t("settings.preferences.saving") : t("settings.preferences.saveSettings")}
      </Button>
    </div>
  )
}
