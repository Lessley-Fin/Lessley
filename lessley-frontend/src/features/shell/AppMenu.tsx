import { useLocation } from "react-router-dom"
import { createPortal } from "react-dom"
import { useTranslation } from "react-i18next"
import { Bell, LogOut, Menu, Settings, Shield, ShieldCheck, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useBodyScrollLock } from "@/hooks/useBodyScrollLock"
import { ROUTES } from "@/lib/routes"
import { MenuNavItem, UnreadDot } from "./components/MenuNavItem"

interface AppMenuProps {
  username: string
  open: boolean
  unreadCount: number
  isAdmin: boolean
  onOpenChange: (open: boolean) => void
  onOpenNotifications: () => void
  onOpenSettings: () => void
  onOpenAdmin: () => void
  onLogout: () => void
}

function getInitials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return "L"
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase()
}

export function AppMenu({
  username,
  open,
  unreadCount,
  isAdmin,
  onOpenChange,
  onOpenNotifications,
  onOpenSettings,
  onOpenAdmin,
  onLogout,
}: AppMenuProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const hasUnread = unreadCount > 0
  const displayName = username.trim() || t("menu.guest")

  const isNotificationsActive = location.pathname === ROUTES.NOTIFICATIONS
  const isSettingsActive = location.pathname === ROUTES.SETTINGS
  const isAdminActive = location.pathname === ROUTES.ADMIN

  useBodyScrollLock(open)

  const closeAnd = (action: () => void) => {
    onOpenChange(false)
    action()
  }

  const menuPortal =
    open && typeof document !== "undefined"
      ? createPortal(
          <div className="fixed inset-0 z-[100] flex justify-center" role="presentation">
            <div className="relative h-[100dvh] w-full max-w-md">
              <button
                type="button"
                className="absolute inset-0 bg-slate-900/50 backdrop-blur-[2px]"
                aria-label={t("menu.closeMenu")}
                tabIndex={open ? 0 : -1}
                onClick={() => onOpenChange(false)}
              />

              <aside
                role="dialog"
                aria-modal="true"
                aria-label={t("menu.navigationMenu")}
                className="absolute bottom-0 start-0 top-0 flex w-[min(85%,20rem)] flex-col overflow-hidden rounded-e-3xl border-e border-slate-200/60 bg-white shadow-[8px_0_40px_hsl(222_47%_11%_/0.12)]"
              >
                <div className="shrink-0 bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 px-5 pb-6 pt-[max(2rem,env(safe-area-inset-top))] text-white">
                  <div className="flex items-start justify-between">
                    <div className="flex min-w-0 items-center gap-3">
                      <div
                        className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-base font-bold backdrop-blur-sm"
                        aria-hidden
                      >
                        {getInitials(displayName)}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-lg font-bold leading-tight">{displayName}</p>
                        <p className="mt-0.5 flex items-center gap-1 text-xs text-blue-100">
                          <Shield className="size-3" aria-hidden />
                          {t("menu.securedAccount")}
                        </p>
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      className="min-h-9 min-w-9 shrink-0 rounded-xl bg-white/10 px-0 text-white hover:bg-white/20 hover:text-white"
                      onClick={() => onOpenChange(false)}
                      aria-label={t("menu.closeMenu")}
                      tabIndex={open ? 0 : -1}
                    >
                      <X className="size-5" />
                    </Button>
                  </div>
                </div>

                <nav className="flex shrink-0 flex-col gap-1 px-3 py-4" role="menu" aria-label={t("menu.mainMenu")}>
                  <MenuNavItem
                    label={t("menu.notifications")}
                    icon={Bell}
                    active={isNotificationsActive}
                    badge={hasUnread ? unreadCount : undefined}
                    showUnreadDot={hasUnread}
                    onClick={() => closeAnd(onOpenNotifications)}
                  />
                  <MenuNavItem
                    label={t("menu.settings")}
                    icon={Settings}
                    active={isSettingsActive}
                    onClick={() => closeAnd(onOpenSettings)}
                  />
                  {isAdmin ? (
                    <MenuNavItem
                      label={t("menu.admin")}
                      icon={ShieldCheck}
                      active={isAdminActive}
                      onClick={() => closeAnd(onOpenAdmin)}
                    />
                  ) : null}
                </nav>

                <div className="mt-auto shrink-0 border-t border-slate-100 px-3 py-4 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
                  <MenuNavItem label={t("menu.signOut")} icon={LogOut} onClick={() => closeAnd(onLogout)} />
                </div>
              </aside>
            </div>
          </div>,
          document.body
        )
      : null

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        className="relative min-h-11 min-w-11 rounded-xl border border-slate-200/80 bg-white px-0 text-slate-700 shadow-sm hover:bg-slate-50"
        onClick={() => onOpenChange(true)}
        aria-label={hasUnread ? t("menu.openMenuWithUnread", { count: unreadCount }) : t("menu.openMenu")}
        aria-expanded={open}
      >
        <Menu className="size-5" />
        {hasUnread ? <UnreadDot className="-end-0.5 -top-0.5" /> : null}
      </Button>
      {menuPortal}
    </>
  )
}
