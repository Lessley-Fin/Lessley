import { LogOut } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/features/auth/store"
import { ROUTES } from "@/lib/routes"

interface LogoutViewProps {
  username: string
}

export function LogoutView({ username }: LogoutViewProps) {
  const navigate = useNavigate()

  function handleLogout() {
    useAuthStore.getState().logout()
    navigate(ROUTES.LOGIN, { replace: true })
  }

  return (
    <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="font-bold">Signed in as {username}</p>
      <p className="text-sm text-muted-foreground">
        Signing out keeps your data safe on this device — your clubs, preferences and connected cards stay exactly
        as they are.
      </p>
      <Button type="button" variant="navy" size="xl" onClick={handleLogout}>
        <LogOut className="size-4" aria-hidden />
        Sign out
      </Button>
    </div>
  )
}
