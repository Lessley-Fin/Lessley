import { useNavigate } from "react-router-dom"

import { useAuthStore } from "@/features/auth/store"
import { fetchMyProfile } from "@/features/user/api"
import { ROUTES } from "@/lib/routes"

// Split from usePostAuth so RegisterWizard can apply the session immediately
// after register+login but defer navigation until the Banking step finishes.
export function useApplyAuthProfile() {
  const login = useAuthStore((s) => s.login)

  return async (profile: { userName: string; email: string }) => {
    const email = profile.email?.trim().toLowerCase() ?? ""

    login({ username: profile.userName, userId: email, email })

    // Enrich with the full profile (cookies are already set, so this is authenticated).
    const full = await fetchMyProfile().catch(() => null)
    if (full) {
      const resolvedEmail = full.email?.trim().toLowerCase() || email
      useAuthStore.getState().setProfile({
        username: full.userName,
        userId: resolvedEmail,
        email: resolvedEmail,
      })
    }
  }
}

export function usePostAuth() {
  const navigate = useNavigate()
  const applyAuthProfile = useApplyAuthProfile()

  return async (profile: { userName: string; email: string }) => {
    await applyAuthProfile(profile)
    navigate(ROUTES.OPTIMIZER, { replace: true })
  }
}
