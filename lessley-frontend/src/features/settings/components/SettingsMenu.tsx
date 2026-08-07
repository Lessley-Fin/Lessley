import { ChevronRight, Globe, Landmark, LogOut, Shield, SlidersHorizontal, User } from "lucide-react"
import { Link } from "react-router-dom"

import type { MeResponse } from "@/features/user/api"
import { ROUTES } from "@/lib/routes"
import type { SettingsView } from "../types"

const MENU_ITEMS = [
  { id: "profile", icon: User, title: "View your profile", desc: "Username and email" },
  { id: "preferences", icon: SlidersHorizontal, title: "Preferences", desc: "Clubs, match level and muted noise" },
  { id: "banking", icon: Landmark, title: "Open banking", desc: "Connected cards" },
  { id: "language", icon: Globe, title: "Language", desc: "English" },
  { id: "logout", icon: LogOut, title: "Log out", desc: "End this session" },
] as const satisfies readonly { id: Exclude<SettingsView, "menu">; icon: typeof User; title: string; desc: string }[]

interface SettingsMenuProps {
  profile: MeResponse
  onNavigate: (view: Exclude<SettingsView, "menu">) => void
}

export function SettingsMenu({ profile, onNavigate }: SettingsMenuProps) {
  const isAdmin = profile.roles.includes("Admin")

  return (
    <>
      <div className="flex items-center gap-3 rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]">
        <span className="flex size-12 items-center justify-center rounded-full bg-accent text-lg font-bold uppercase text-accent-foreground">
          {profile.userName.charAt(0)}
        </span>
        <div>
          <p className="font-semibold">{profile.userName}</p>
          <p className="text-xs text-muted-foreground">{profile.email}</p>
        </div>
      </div>

      <ul className="overflow-hidden rounded-3xl bg-card shadow-[var(--shadow-card)]">
        {MENU_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onNavigate(item.id)}
              className="flex w-full items-center gap-3 border-b border-border p-4 text-left last:border-0 hover:bg-secondary"
            >
              <span className="flex size-9 items-center justify-center rounded-full bg-secondary">
                <item.icon className="size-4 text-primary" aria-hidden />
              </span>
              <div className="flex-1">
                <p className="text-sm font-semibold">{item.title}</p>
                <p className="text-xs text-muted-foreground">{item.desc}</p>
              </div>
              <ChevronRight className="size-4 text-muted-foreground" aria-hidden />
            </button>
          </li>
        ))}
      </ul>

      {isAdmin ? (
        <Link
          to={ROUTES.ADMIN}
          className="flex items-center gap-3 rounded-3xl bg-card p-4 shadow-[var(--shadow-card)]"
        >
          <span className="flex size-9 items-center justify-center rounded-full bg-secondary">
            <Shield className="size-4 text-primary" aria-hidden />
          </span>
          <div className="flex-1">
            <p className="text-sm font-semibold">Admin console</p>
            <p className="text-xs text-muted-foreground">Roles, tags and notifications</p>
          </div>
          <ChevronRight className="size-4 text-muted-foreground" aria-hidden />
        </Link>
      ) : null}
    </>
  )
}
