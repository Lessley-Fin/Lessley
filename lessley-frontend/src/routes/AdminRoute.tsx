import { Navigate, Outlet } from "react-router-dom"

import { useMyProfile } from "@/features/user/hooks"
import { ROUTES } from "@/lib/routes"

export function AdminRoute() {
  const { data: profile, isLoading } = useMyProfile()

  if (isLoading) return null

  if (!profile?.roles?.includes("Admin")) {
    return <Navigate to={ROUTES.OPTIMIZER} replace />
  }

  return <Outlet />
}
