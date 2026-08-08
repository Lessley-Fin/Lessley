import { LogOut } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/features/auth/store"
import { ROUTES } from "@/lib/routes"

interface LogoutViewProps {
  username: string
}

export function LogoutView({ username }: LogoutViewProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  function handleLogout() {
    useAuthStore.getState().logout()
    navigate(ROUTES.LOGIN, { replace: true })
  }

  return (
    <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="font-bold">{t("settings.logout.signedInAs", { username })}</p>
      <p className="text-sm text-muted-foreground">{t("settings.logout.notice")}</p>
      <Button type="button" variant="navy" size="xl" onClick={handleLogout}>
        <LogOut className="size-4" aria-hidden />
        {t("settings.logout.signOut")}
      </Button>
    </div>
  )
}
