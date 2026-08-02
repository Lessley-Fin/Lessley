import { Navigate, Outlet } from "react-router-dom"

import { useAuthStore } from "@/features/auth/store"
import { ROUTES } from "@/lib/routes"

export function GuestRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (isAuthenticated) {
    return <Navigate to={ROUTES.OPTIMIZER} replace />
  }

  return <Outlet />
}
