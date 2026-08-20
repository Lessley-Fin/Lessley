import { useEffect, useRef } from "react"
import { Outlet } from "react-router-dom"

import { useSignalR } from "@/features/notifications/useSignalR"
import { MainShell } from "@/features/shell/MainShell"
import { useMyProfile, useSendWelcomeNotification } from "@/features/user/hooks"

export function AppLayout() {
  const { isConnected } = useSignalR()
  const { data: profile } = useMyProfile()
  const { mutate: sendWelcomeNotification } = useSendWelcomeNotification()

  // Fires once per user, ever — gated server-side by ApplicationUser.WelcomeNotificationSent.
  // Waiting for isConnected before calling means the server's SignalR push actually has a live
  // socket to land on, so the toast pops immediately instead of only appearing after a refetch.
  const welcomeTriggered = useRef(false)
  useEffect(() => {
    if (isConnected && profile?.pendingWelcomeNotification && !welcomeTriggered.current) {
      welcomeTriggered.current = true
      sendWelcomeNotification()
    }
  }, [isConnected, profile?.pendingWelcomeNotification, sendWelcomeNotification])

  return (
    <MainShell>
      <Outlet />
    </MainShell>
  )
}
