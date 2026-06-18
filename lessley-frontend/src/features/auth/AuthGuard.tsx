import type { ReactNode } from "react"

interface AuthGuardProps {
  isAuthenticated: boolean
  children: ReactNode
  fallback: ReactNode
}

// Renders children when the user is authenticated; otherwise renders fallback.
export function AuthGuard({ isAuthenticated, children, fallback }: AuthGuardProps) {
  return isAuthenticated ? <>{children}</> : <>{fallback}</>
}
