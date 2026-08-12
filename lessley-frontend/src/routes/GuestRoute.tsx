import { Navigate, Outlet } from "react-router-dom"

import { useAuthStore } from "@/features/auth/store"
import { ROUTES } from "@/lib/routes"

export function GuestRoute() {
  const status = useAuthStore((s) => s.status)
  const registrationInProgress = useAuthStore((s) => s.registrationInProgress)

  if (status === "loading") return null

  if (status === "authenticated" && !registrationInProgress) {
    return <Navigate to={ROUTES.OPTIMIZER} replace />
  }

  return <Outlet />
}
