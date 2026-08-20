import { ChevronRight, Globe, Landmark, LogOut, Shield, SlidersHorizontal, User } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import type { MeResponse } from "@/features/user/api"
import { ROUTES } from "@/lib/routes"
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from "@/lib/i18n/config"
import type { SettingsView } from "../types"

const LANGUAGE_NAMES: Record<SupportedLanguage, string> = {
  en: "English",
  he: "עברית",
}

interface SettingsMenuProps {
  profile: MeResponse
  onNavigate: (view: Exclude<SettingsView, "menu">) => void
}

export function SettingsMenu({ profile, onNavigate }: SettingsMenuProps) {
  const { t, i18n } = useTranslation()
  const isAdmin = profile.roles.includes("Admin")
  const currentLanguageName = LANGUAGE_NAMES[i18n.language as SupportedLanguage] ?? LANGUAGE_NAMES[SUPPORTED_LANGUAGES[0]]

  const MENU_ITEMS = [
    { id: "profile", icon: User, title: t("settings.menu.profileTitle"), desc: t("settings.menu.profileDesc") },
    { id: "preferences", icon: SlidersHorizontal, title: t("settings.menu.preferencesTitle"), desc: t("settings.menu.preferencesDesc") },
    { id: "banking", icon: Landmark, title: t("settings.menu.bankingTitle"), desc: t("settings.menu.bankingDesc") },
    { id: "language", icon: Globe, title: t("settings.menu.languageTitle"), desc: currentLanguageName },
    { id: "logout", icon: LogOut, title: t("settings.menu.logoutTitle"), desc: t("settings.menu.logoutDesc") },
  ] as const satisfies readonly { id: Exclude<SettingsView, "menu">; icon: typeof User; title: string; desc: string }[]

  return (
    <>
      <div className="flex items-center gap-3 rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]">
        <span className="flex size-12 items-center justify-center rounded-full bg-accent text-lg font-bold uppercase text-accent-foreground">
          {profile.userName.charAt(0)}
        </span>
        <div>
          <p className="font-semibold">{profile.userName}</p>
          <p className="text-xs text-muted-foreground">{profile.email}</p>
        </div>
      </div>

      <ul className="overflow-hidden rounded-3xl bg-card shadow-[var(--shadow-card)]">
        {MENU_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onNavigate(item.id)}
              className="flex w-full items-center gap-3 border-b border-border p-4 text-start last:border-0 hover:bg-secondary"
            >
              <span className="flex size-9 items-center justify-center rounded-full bg-secondary">
                <item.icon className="size-4 text-primary" aria-hidden />
              </span>
              <div className="flex-1">
                <p className="text-sm font-semibold">{item.title}</p>
                <p className="text-xs text-muted-foreground">{item.desc}</p>
              </div>
              <ChevronRight className="size-4 text-muted-foreground rtl:rotate-180" aria-hidden />
            </button>
          </li>
        ))}
      </ul>

      {isAdmin ? (
        <Link
          to={ROUTES.ADMIN}
          className="flex items-center gap-3 rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]"
        >
          <span className="flex size-9 items-center justify-center rounded-full bg-secondary">
            <Shield className="size-4 text-primary" aria-hidden />
          </span>
          <div className="flex-1">
            <p className="text-sm font-semibold">{t("settings.menu.adminConsoleTitle")}</p>
            <p className="text-xs text-muted-foreground">{t("settings.menu.adminConsoleDesc")}</p>
          </div>
          <ChevronRight className="size-4 text-muted-foreground rtl:rotate-180" aria-hidden />
        </Link>
      ) : null}
    </>
  )
}
