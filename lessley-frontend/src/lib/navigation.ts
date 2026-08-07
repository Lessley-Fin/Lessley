import { ChartColumn, Flame, Lightbulb, Sparkles } from "lucide-react"
import { ROUTES } from "./routes"

export const MAIN_TABS = [
  { id: "insights", label: "Insights", icon: ChartColumn, path: ROUTES.INSIGHTS },
  { id: "hot-deals", label: "Hot", icon: Flame, path: ROUTES.HOT_DEALS },
  { id: "optimizer", label: "Optimizer", icon: Sparkles, path: ROUTES.OPTIMIZER },
  { id: "recommendations", label: "Recommend", icon: Lightbulb, path: ROUTES.RECOMMENDATIONS },
] as const

// The bottom nav stays visible on every authenticated route, including Notifications,
// Settings and Admin — verified against the prototype's own markup for each of those pages.
export const OVERLAY_ROUTES = [] as const

export type MainTab = (typeof MAIN_TABS)[number]["id"]

export function deriveActiveTab(pathname: string): MainTab {
  const match = MAIN_TABS.find((tab) => pathname.startsWith(tab.path))
  return match?.id ?? "optimizer"
}
