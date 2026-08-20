import type { ReactNode } from "react"
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

  return (
    <div className="app-shell">
      <header
        className="flex items-center border-b border-border/70 bg-card/80 px-4 py-3 backdrop-blur sm:px-6"
        style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
      >
        <div className="app-content-width flex items-center gap-3">
          <img src={logoUrl} alt={t("common.appName")} className="size-12 shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-bold leading-tight">{t("common.appName")}</p>
            <p className="truncate text-xs text-muted-foreground">{t("common.tagline")}</p>
          </div>
          <Link
            to={ROUTES.QA}
            aria-label={t("nav.qa")}
            className="flex size-10 shrink-0 items-center justify-center rounded-full border border-border bg-card shadow-[var(--shadow-card)]"
          >
            <HelpCircle className="size-[18px]" aria-hidden />
          </Link>
          <Link
            to={ROUTES.NOTIFICATIONS}
            aria-label={t("nav.notifications")}
            className="relative flex size-10 shrink-0 items-center justify-center rounded-full border border-border bg-card shadow-[var(--shadow-card)]"
          >
            <Bell className="size-[18px]" aria-hidden />
            {unreadCount > 0 ? (
              <span className="absolute end-1.5 top-1.5 size-2.5 rounded-full bg-warning ring-2 ring-card" />
            ) : null}
          </Link>
          <Link
            to={ROUTES.SETTINGS}
            aria-label={t("nav.profileAndSettings")}
            className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-bold uppercase text-accent-foreground"
          >
            {avatarInitial}
          </Link>
        </div>
      </header>

      <main className="no-scrollbar flex-1 overflow-y-auto px-4 pb-2 pt-4 sm:px-6">
        <div className="app-content-width">{children}</div>
      </main>

      {showBottomNav ? (
        <nav
          className="px-4 pb-4 sm:px-6"
          style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
          aria-label="Main navigation"
        >
          <div className="app-content-width surface-navy flex items-center justify-between rounded-full px-2 py-2 shadow-[var(--shadow-float)]">
            {MAIN_TABS.map((tab) => {
              const isActive = activeTab === tab.id
              return (
                <Link
                  key={tab.id}
                  to={tab.path}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex flex-1 flex-col items-center gap-1 rounded-full px-1 py-2 text-[11px] font-medium transition-all",
                    isActive ? "surface-teal shadow-[var(--shadow-card)]" : "text-navy-muted hover:text-navy-foreground"
                  )}
                >
                  <tab.icon className="size-[18px]" aria-hidden />
                  {t(tab.labelKey)}
                </Link>
              )
            })}
          </div>
        </nav>
      ) : null}
    </div>
  )
}
