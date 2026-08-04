import { Navigate, Outlet } from "react-router-dom"

import { useAuthStore } from "@/features/auth/store"
import { ROUTES } from "@/lib/routes"

export function ProtectedRoute() {
  const status = useAuthStore((s) => s.status)

  // Wait for the initial cookie probe before deciding, so a reload doesn't flash /login.
  if (status === "loading") return null

  if (status !== "authenticated") {
    return <Navigate to={ROUTES.LOGIN} replace />
  }

  return <Outlet />
}
