import { useNavigate } from "react-router-dom"
import { SlidersHorizontal } from "lucide-react"

import { EmptyState } from "@/components/shared/EmptyState"
import { PageHeader } from "@/components/shared/PageHeader"

export function SettingsPage() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader title="Settings" onBack={() => navigate(-1)} />

      <div className="flex flex-1 items-center justify-center px-5 py-8">
        <EmptyState
          icon={SlidersHorizontal}
          title="Preferences coming soon"
          description="Account controls and notification settings will live here."
        />
      </div>
    </div>
  )
}
