import type { ReactNode } from "react"
import { BarChart3, LogOut, ScanSearch } from "lucide-react"

import { Button } from "@/components/ui/button"

export type MainTab = "optimizer" | "insights"

interface MainShellProps {
  username: string
  activeTab: MainTab
  onTabChange: (tab: MainTab) => void
  onLogout: () => void
  children: ReactNode
}

export function MainShell({ username, activeTab, onTabChange, onLogout, children }: MainShellProps) {
  return (
    <div className="mx-auto flex min-h-svh w-full max-w-md flex-col bg-slate-50">
      <header className="sticky top-0 z-20 flex min-h-16 shrink-0 items-center justify-between bg-slate-50/95 px-6 pt-3 backdrop-blur">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Lessley</h1>
          <p className="text-sm text-slate-500">Hi {username}</p>
        </div>
        <Button
          className="min-h-11 min-w-11 rounded-xl border-0 bg-white px-3 text-slate-700 shadow-sm hover:bg-slate-100"
          variant="ghost"
          onClick={onLogout}
          aria-label="Logout"
        >
          <LogOut className="size-4" />
          Logout
        </Button>
      </header>

      <div className="min-h-0 flex-1 pb-24">{children}</div>

      <nav
        className="fixed bottom-0 left-0 right-0 z-30 border-t border-slate-200/90 bg-white/95 pb-[max(0.5rem,env(safe-area-inset-bottom))] backdrop-blur-md"
        aria-label="Main navigation"
      >
        <div className="mx-auto flex max-w-md gap-1 px-2 py-2">
          <button
            type="button"
            onClick={() => onTabChange("optimizer")}
            className={
              activeTab === "optimizer"
                ? "flex flex-1 flex-col items-center gap-1 rounded-xl bg-slate-900 py-2.5 text-white shadow-sm transition-colors"
                : "flex flex-1 flex-col items-center gap-1 rounded-xl py-2.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
            }
            aria-current={activeTab === "optimizer" ? "page" : undefined}
          >
            <ScanSearch className="size-5" aria-hidden />
            <span className="text-[11px] font-medium leading-tight">Optimizer</span>
          </button>
          <button
            type="button"
            onClick={() => onTabChange("insights")}
            className={
              activeTab === "insights"
                ? "flex flex-1 flex-col items-center gap-1 rounded-xl bg-slate-900 py-2.5 text-white shadow-sm transition-colors"
                : "flex flex-1 flex-col items-center gap-1 rounded-xl py-2.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
            }
            aria-current={activeTab === "insights" ? "page" : undefined}
          >
            <BarChart3 className="size-5" aria-hidden />
            <span className="text-center text-[11px] font-medium leading-tight">
              Insights &amp;
              <br />
              recommendations
            </span>
          </button>
        </div>
      </nav>
    </div>
  )
}
