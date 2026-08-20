import { Outlet } from "react-router-dom"

export function AuthLayout() {
  return (
    <div className="app-shell">
      <main className="app-auth-main">
        <Outlet />
      </main>
    </div>
  )
}
