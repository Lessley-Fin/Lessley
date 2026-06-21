import { Outlet } from "react-router-dom"
import { Toaster } from "sonner"

import { useSignalR } from "@/features/notifications/useSignalR"
import { MainShell } from "@/features/shell/MainShell"
import { useMyProfile } from "@/features/user/hooks"

export function AppLayout() {
  useSignalR()
  useMyProfile()

  return (
    <>
      <MainShell>
        <Outlet />
      </MainShell>
      <Toaster position="top-center" richColors expand visibleToasts={3} />
    </>
  )
}
