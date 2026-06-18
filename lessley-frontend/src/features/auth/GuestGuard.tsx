import type { ReactNode } from "react"

interface GuestGuardProps {
  isAuthenticated: boolean
  children: ReactNode
  fallback: ReactNode
}

// Renders children only when NOT authenticated (guest).
// Use to block authenticated users from reaching login/register pages.
export function GuestGuard({ isAuthenticated, children, fallback }: GuestGuardProps) {
  return isAuthenticated ? <>{fallback}</> : <>{children}</>
}
