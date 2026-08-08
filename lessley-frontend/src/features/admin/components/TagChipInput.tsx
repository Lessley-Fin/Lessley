import { useState } from "react"
import type { KeyboardEvent } from "react"
import { X } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Input } from "@/components/ui/input"

interface TagChipInputProps {
  value: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
}

export function TagChipInput({ value, onChange, placeholder }: TagChipInputProps) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState("")

  function commitDraft() {
    const tag = draft.trim().replace(/^#/, "")
    if (tag && !value.includes(tag)) {
      onChange([...value, tag])
    }
    setDraft("")
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      commitDraft()
    } else if (e.key === "Backspace" && !draft && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  return (
    <div className="space-y-2">
      {value.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {value.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => onChange(value.filter((t) => t !== tag))}
              className="flex items-center gap-1 rounded-full border border-primary bg-accent px-3 py-1.5 text-xs font-medium text-accent-foreground"
            >
              #{tag}
              <X className="size-3" aria-hidden />
            </button>
          ))}
        </div>
      ) : null}
      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commitDraft}
        placeholder={placeholder ?? t("admin.tagChipInput.placeholder")}
        className="h-12 rounded-2xl"
      />
    </div>
  )
}
