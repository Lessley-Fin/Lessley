import { useEffect, useRef } from "react"
import { Outlet } from "react-router-dom"

import { useSignalR } from "@/features/notifications/useSignalR"
import { MainShell } from "@/features/shell/MainShell"
import { useMyProfile, useSendWelcomeNotification } from "@/features/user/hooks"

export function AppLayout() {
  useSignalR()
  const { data: profile } = useMyProfile()
  const { mutate: sendWelcomeNotification } = useSendWelcomeNotification()

  // Fires once per user, ever — gated server-side by ApplicationUser.WelcomeNotificationSent.
  // This ref just stops a duplicate call within the same mount (e.g. a profile refetch).
  const welcomeTriggered = useRef(false)
  useEffect(() => {
    if (profile?.pendingWelcomeNotification && !welcomeTriggered.current) {
      welcomeTriggered.current = true
      sendWelcomeNotification()
    }
  }, [profile?.pendingWelcomeNotification, sendWelcomeNotification])

  return (
    <MainShell>
      <Outlet />
    </MainShell>
  )
}
