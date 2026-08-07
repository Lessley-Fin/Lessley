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
  return (
    <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Account</p>
      <Row label="Username" value={profile.userName} />
      <Row label="Email" value={profile.email} />
      <Row label="Role" value={profile.roles.join(", ") || "User"} />
    </div>
  )
}
