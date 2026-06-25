import { useState, type ReactNode } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import { useAuthStore } from "@/features/auth/store"
import { useUnreadCount } from "@/features/notifications/hooks"
import { useMyProfile } from "@/features/user/hooks"
import { MAIN_TABS, OVERLAY_ROUTES, deriveActiveTab } from "@/lib/navigation"
import { ROUTES } from "@/lib/routes"
import { cn } from "@/lib/utils"
import { AppMenu } from "./AppMenu"

export function MainShell({ children }: { children: ReactNode }) {
  const username = useAuthStore((s) => s.username)
  const unreadCount = useUnreadCount()
  const { data: profile } = useMyProfile()
  const isAdmin = profile?.roles.includes("Admin") ?? false
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const activeTab = deriveActiveTab(location.pathname)
  const showBottomNav = !(OVERLAY_ROUTES as readonly string[]).includes(location.pathname)

  const handleLogout = () => {
    useAuthStore.getState().logout()
    navigate(ROUTES.LOGIN, { replace: true })
  }

  return (
    <div className="fintech-shell">
      <header className="sticky top-0 z-20 shrink-0 border-b border-violet-100/60 bg-white/80 px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] backdrop-blur-xl sm:px-5">
        <div className="flex min-h-14 items-center gap-3">
          <AppMenu
            username={username}
            open={menuOpen}
            unreadCount={unreadCount}
            isAdmin={isAdmin}
            onOpenChange={setMenuOpen}
            onOpenNotifications={() => navigate(ROUTES.NOTIFICATIONS)}
            onOpenSettings={() => navigate(ROUTES.SETTINGS)}
            onOpenAdmin={() => navigate(ROUTES.ADMIN)}
            onLogout={handleLogout}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="fintech-logo-mark" aria-hidden>
                L
              </span>
              <div className="min-w-0">
                <h1 className="text-lg font-bold tracking-tight text-slate-900">Lessley</h1>
                <p className="truncate text-xs text-slate-500">
                  Welcome back, <span className="font-medium text-slate-700">{username}</span>
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className={showBottomNav ? "min-h-0 flex-1 pb-[calc(6.25rem+env(safe-area-inset-bottom))]" : "min-h-0 flex-1"}>
        {children}
      </div>

      {showBottomNav ? (
        <nav
          className="pointer-events-none fixed bottom-0 left-0 right-0 z-30 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
          aria-label="Main navigation"
        >
          <div className="fintech-nav-bar pointer-events-auto mx-auto max-w-md">
            {MAIN_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => navigate(tab.path)}
                className={cn(
                  "fintech-nav-pill",
                  activeTab === tab.id ? "fintech-nav-pill-active" : "fintech-nav-pill-inactive"
                )}
                aria-current={activeTab === tab.id ? "page" : undefined}
              >
                <tab.icon className="size-5" aria-hidden />
                <span className="text-center leading-tight">
                  {tab.label}
                  {"subtitle" in tab && tab.subtitle ? (
                    <span className="block text-[10px] font-normal opacity-80">{tab.subtitle}</span>
                  ) : null}
                </span>
              </button>
            ))}
          </div>
        </nav>
      ) : null}
    </div>
  )
}
