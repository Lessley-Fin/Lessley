import { useEffect, type ReactNode } from "react"
import { Bell, HelpCircle } from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { useTranslation } from "react-i18next"

import logoUrl from "../../../assets/logo-without-name.svg"
import { useAuthStore } from "@/features/auth/store"
import { useUnreadCount } from "@/features/notifications/hooks"
import { MAIN_TABS, OVERLAY_ROUTES, deriveActiveTab } from "@/lib/navigation"
import { ROUTES } from "@/lib/routes"
import { cn } from "@/lib/utils"

export function MainShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const username = useAuthStore((s) => s.username)
  const unreadCount = useUnreadCount()
  const location = useLocation()

  const activeTab = deriveActiveTab(location.pathname)
  const showBottomNav = !(OVERLAY_ROUTES as readonly string[]).includes(location.pathname)
  const avatarInitial = (username.trim().charAt(0) || "L").toUpperCase()

  // The page itself scrolls now, so a new route has to start at the top instead of
  // inheriting the previous one's offset. Query-string changes (the Optimizer's
  // own tabs) deliberately keep their position.
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" })
  }, [location.pathname])

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-content-width flex items-center gap-2 sm:gap-3">
          <img src={logoUrl} alt={t("common.appName")} className="size-10 shrink-0 sm:size-12" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold leading-tight sm:text-[15px]">{t("common.appName")}</p>
            <p className="truncate text-[11px] text-muted-foreground sm:text-xs">{t("common.tagline")}</p>
          </div>
          <Link
            to={ROUTES.QA}
            aria-label={t("nav.qa")}
            className="flex size-9 shrink-0 items-center justify-center rounded-full border border-border bg-card shadow-[var(--shadow-card)] sm:size-10"
          >
            <HelpCircle className="size-[18px]" aria-hidden />
          </Link>
          <Link
            to={ROUTES.NOTIFICATIONS}
            aria-label={t("nav.notifications")}
            className="relative flex size-9 shrink-0 items-center justify-center rounded-full border border-border bg-card shadow-[var(--shadow-card)] sm:size-10"
          >
            <Bell className="size-[18px]" aria-hidden />
            {unreadCount > 0 ? (
              <span className="absolute end-1.5 top-1.5 size-2.5 rounded-full bg-warning ring-2 ring-card" />
            ) : null}
          </Link>
          <Link
            to={ROUTES.SETTINGS}
            aria-label={t("nav.profileAndSettings")}
            className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-bold uppercase text-accent-foreground sm:size-10"
          >
            {avatarInitial}
          </Link>
        </div>
      </header>

      <main className="app-main">
        <div className="app-content-width">{children}</div>
      </main>

      {showBottomNav ? (
        <nav className="app-bottom-nav" aria-label="Main navigation">
          <div className="app-content-width surface-navy flex items-stretch justify-between gap-1 rounded-full p-2 shadow-[var(--shadow-float)]">
            {MAIN_TABS.map((tab) => {
              const isActive = activeTab === tab.id
              return (
                <Link
                  key={tab.id}
                  to={tab.path}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "app-nav-tab",
                    isActive ? "surface-teal shadow-[var(--shadow-card)]" : "text-navy-muted hover:text-navy-foreground"
                  )}
                >
                  <tab.icon className="size-[18px] shrink-0" aria-hidden />
                  <span className="max-w-full truncate">{t(tab.labelKey)}</span>
                </Link>
              )
            })}
          </div>
        </nav>
      ) : null}
    </div>
  )
}
