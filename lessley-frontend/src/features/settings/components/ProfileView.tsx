import { useTranslation } from "react-i18next"

import type { MeResponse } from "@/features/user/api"

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-secondary p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold">{value}</p>
    </div>
  )
}

interface ProfileViewProps {
  profile: MeResponse
}

export function ProfileView({ profile }: ProfileViewProps) {
  const { t } = useTranslation()
  return (
    <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{t("settings.profile.account")}</p>
      <Row label={t("settings.profile.username")} value={profile.userName} />
      <Row label={t("settings.profile.email")} value={profile.email} />
      <Row label={t("settings.profile.role")} value={profile.roles.join(", ") || t("settings.profile.defaultRole")} />
    </div>
  )
}
