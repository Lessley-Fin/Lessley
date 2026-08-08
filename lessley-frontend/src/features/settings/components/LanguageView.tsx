import { Check } from "lucide-react"
import { useTranslation } from "react-i18next"

import { SUPPORTED_LANGUAGES, setLanguage, type SupportedLanguage } from "@/lib/i18n/config"
import { cn } from "@/lib/utils"

const LANGUAGE_NAMES: Record<SupportedLanguage, string> = {
  en: "English",
  he: "עברית",
}

export function LanguageView() {
  const { t, i18n } = useTranslation()
  const activeLanguage = i18n.language as SupportedLanguage

  return (
    <div className="space-y-2 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{t("settings.language.title")}</p>
      {SUPPORTED_LANGUAGES.map((language) => {
        const isActive = activeLanguage === language
        return (
          <button
            key={language}
            type="button"
            onClick={() => setLanguage(language)}
            aria-pressed={isActive}
            className={cn(
              "flex w-full items-center justify-between rounded-2xl p-3 text-sm font-medium transition-colors",
              isActive ? "bg-accent text-accent-foreground" : "bg-transparent text-foreground hover:bg-accent/60"
            )}
          >
            {LANGUAGE_NAMES[language]}
            {isActive ? <Check className="size-4" aria-hidden /> : null}
          </button>
        )
      })}
    </div>
  )
}
