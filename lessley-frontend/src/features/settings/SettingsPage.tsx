import { useState } from "react"
import { ArrowLeft } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { useMyProfile } from "@/features/user/hooks"
import { BankingView } from "./components/BankingView"
import { LanguageView } from "./components/LanguageView"
import { LogoutView } from "./components/LogoutView"
import { PreferencesView } from "./components/PreferencesView"
import { ProfileView } from "./components/ProfileView"
import { QAView } from "./components/QAView"
import { SettingsMenu } from "./components/SettingsMenu"
import type { SettingsView } from "./types"

export function SettingsPage() {
  const { t } = useTranslation()
  const [view, setView] = useState<SettingsView>("menu")
  const { data: profile, isLoading, error } = useMyProfile()

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center gap-3">
        {view !== "menu" ? (
          <Button type="button" variant="pill" size="icon" aria-label={t("common.back")} onClick={() => setView("menu")}>
            <ArrowLeft className="rtl:rotate-180" aria-hidden />
          </Button>
        ) : null}
        <h1 className="text-2xl font-bold tracking-tight">{t("settings.page.title")}</h1>
      </div>

      <div className="no-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto pb-2">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">{t("settings.page.loading")}</p>
        ) : error || !profile ? (
          <p className="text-sm text-destructive">{t("settings.page.loadError")}</p>
        ) : (
          <>
            {view === "menu" ? <SettingsMenu profile={profile} onNavigate={setView} /> : null}
            {view === "profile" ? <ProfileView profile={profile} /> : null}
            {view === "preferences" ? <PreferencesView profile={profile} /> : null}
            {view === "banking" ? <BankingView /> : null}
            {view === "language" ? <LanguageView /> : null}
            {view === "qa" ? <QAView /> : null}
            {view === "logout" ? <LogoutView username={profile.userName} /> : null}
          </>
        )}
      </div>
    </div>
  )
}
