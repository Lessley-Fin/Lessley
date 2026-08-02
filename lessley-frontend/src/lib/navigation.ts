import { BarChart3, Lightbulb, ScanSearch, Tag } from "lucide-react"
import { ROUTES } from "./routes"

export const MAIN_TABS = [
  { id: "optimizer", label: "Optimizer", icon: ScanSearch, path: ROUTES.OPTIMIZER },
  {
    id: "insights",
    label: "Insights",
    subtitle: "& clubs",
    icon: BarChart3,
    path: ROUTES.INSIGHTS,
  },
  { id: "recommendations", label: "Recomendation", icon: Lightbulb, path: ROUTES.RECOMMENDATIONS },
  { id: "deal-finder", label: "Deal", subtitle: "Finder", icon: Tag, path: ROUTES.DEAL_FINDER },
] as const

export const OVERLAY_ROUTES = [ROUTES.NOTIFICATIONS, ROUTES.SETTINGS, ROUTES.ADMIN] as const

export type MainTab = (typeof MAIN_TABS)[number]["id"]

export function deriveActiveTab(pathname: string): MainTab {
  const match = MAIN_TABS.find((tab) => pathname.startsWith(tab.path))
  return match?.id ?? "optimizer"
}
