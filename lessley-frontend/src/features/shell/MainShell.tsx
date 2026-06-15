import { useState, type ReactNode } from "react"

import { BarChart3, ScanSearch } from "lucide-react"



import { AppMenu } from "@/features/shell/AppMenu"

import { cn } from "@/lib/utils"



export type MainTab = "optimizer" | "insights"



interface MainShellProps {

  username: string

  activeTab: MainTab

  unreadCount: number

  showNotifications?: boolean

  showSettings?: boolean

  showBottomNav?: boolean

  onTabChange: (tab: MainTab) => void

  onOpenNotifications: () => void

  onOpenSettings: () => void

  onLogout: () => void

  children: ReactNode

}



export function MainShell({

  username,

  activeTab,

  unreadCount,

  showNotifications = false,

  showSettings = false,

  showBottomNav = true,

  onTabChange,

  onOpenNotifications,

  onOpenSettings,

  onLogout,

  children,

}: MainShellProps) {

  const [menuOpen, setMenuOpen] = useState(false)



  return (

    <div className="fintech-shell">

      <header className="sticky top-0 z-20 shrink-0 border-b border-violet-100/60 bg-white/80 px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] backdrop-blur-xl sm:px-5">

        <div className="flex min-h-14 items-center gap-3">

          <AppMenu

            username={username}

            open={menuOpen}

            unreadCount={unreadCount}

            showNotifications={showNotifications}

            showSettings={showSettings}

            onOpenChange={setMenuOpen}

            onOpenNotifications={onOpenNotifications}

            onOpenSettings={onOpenSettings}

            onLogout={onLogout}

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

            <button

              type="button"

              onClick={() => onTabChange("optimizer")}

              className={cn(

                "fintech-nav-pill",

                activeTab === "optimizer" ? "fintech-nav-pill-active" : "fintech-nav-pill-inactive"

              )}

              aria-current={activeTab === "optimizer" ? "page" : undefined}

            >

              <ScanSearch className="size-5" aria-hidden />

              <span>Optimizer</span>

            </button>

            <button

              type="button"

              onClick={() => onTabChange("insights")}

              className={cn(

                "fintech-nav-pill",

                activeTab === "insights" ? "fintech-nav-pill-active" : "fintech-nav-pill-inactive"

              )}

              aria-current={activeTab === "insights" ? "page" : undefined}

            >

              <BarChart3 className="size-5" aria-hidden />

              <span className="text-center leading-tight">

                Insights

                <span className="block text-[10px] font-normal opacity-80">&amp; clubs</span>

              </span>

            </button>

          </div>

        </nav>

      ) : null}

    </div>

  )

}

