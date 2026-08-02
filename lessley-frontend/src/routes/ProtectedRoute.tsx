import { Navigate, Outlet } from "react-router-dom"

import { useAuthStore } from "@/features/auth/store"
import { ROUTES } from "@/lib/routes"

export function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />
  }

  return <Outlet />
}
