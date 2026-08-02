import { useNavigate } from "react-router-dom"

import { useAuthStore } from "@/features/auth/store"
import { fetchMyProfile } from "@/features/user/api"
import { getEmailFromToken } from "@/lib/auth"
import { ROUTES } from "@/lib/routes"

export function usePostAuth() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)

  return async (session: { accessToken: string; refreshToken: string; userName: string; email?: string }) => {
    const tokenEmail = session.email ?? getEmailFromToken(session.accessToken)

    login({
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      username: session.userName,
      userId: tokenEmail,
      email: tokenEmail,
    })

    const profile = await fetchMyProfile().catch(() => null)
    if (profile) {
      const resolvedEmail = profile.email?.trim().toLowerCase() || tokenEmail
      useAuthStore.getState().setProfile({
        username: profile.userName,
        userId: resolvedEmail,
        email: resolvedEmail,
      })
    }

    navigate(ROUTES.OPTIMIZER, { replace: true })
  }
}
