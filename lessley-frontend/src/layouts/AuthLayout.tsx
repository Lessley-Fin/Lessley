import { Outlet } from "react-router-dom"

export function AuthLayout() {
  return (
    <div className="app-shell">
      <main className="no-scrollbar flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
