import { useState } from "react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { useClubs } from "@/features/clubs/hooks"
import type { MeResponse } from "@/features/user/api"
import { useUpdateMyProfile } from "@/features/user/hooks"
import { MATCH_LEVEL_OPTIONS, emojiForClub, formatCategoryLabel } from "@/lib/constants"
import { cn, toggleArrayValue } from "@/lib/utils"

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
        active ? "border-primary bg-accent text-accent-foreground" : "border-border bg-card text-muted-foreground",
      )}
    >
      {children}
    </button>
  )
}

interface PreferencesViewProps {
  profile: MeResponse
}

export function PreferencesView({ profile }: PreferencesViewProps) {
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
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Loyalty clubs</p>
        <div className="flex flex-wrap gap-2">
          {clubs.map((club) => (
            <Chip
              key={club.id}
              active={selectedClubs.includes(club.id)}
              onClick={() => setSelectedClubs((prev) => toggleArrayValue(prev, club.id))}
            >
              {emojiForClub(club.name)} {club.name}
            </Chip>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Match level</p>
        <div className="flex flex-wrap gap-2">
          {MATCH_LEVEL_OPTIONS.map((opt) => (
            <Chip key={opt.value} active={matchLevel === opt.value} onClick={() => setMatchLevel(opt.value)}>
              {opt.label}
            </Chip>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Muted categories</p>
        {profile.tags.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No tags yet — connect your bank to see available tags.
          </p>
        ) : (
          <div className="no-scrollbar flex max-h-44 flex-wrap gap-2 overflow-y-auto pr-1">
            {profile.tags.map((tag) => (
              <Chip
                key={tag}
                active={mutedTags.includes(tag)}
                onClick={() => setMutedTags((prev) => toggleArrayValue(prev, tag))}
              >
                {formatCategoryLabel(tag)}
              </Chip>
            ))}
          </div>
        )}
      </div>

      {updateProfile.error ? (
        <p className="text-xs text-destructive">
          {updateProfile.error instanceof Error ? updateProfile.error.message : "Failed to save settings."}
        </p>
      ) : null}
      {updateProfile.isSuccess ? <p className="text-xs text-success">Settings saved</p> : null}

      <Button type="button" variant="hero" size="xl" onClick={handleSave} disabled={updateProfile.isPending}>
        {updateProfile.isPending ? "Saving..." : "Save settings"}
      </Button>
    </div>
  )
}
