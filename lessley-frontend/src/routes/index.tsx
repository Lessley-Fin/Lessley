import { lazy, Suspense } from "react"
import {
  createBrowserRouter,
  Navigate,
} from "react-router-dom"

import { ErrorBoundary } from "@/components/ErrorBoundary"
import { AppLayout } from "@/layouts/AppLayout"
import { ROUTES } from "@/lib/routes"
import { ProtectedRoute } from "./ProtectedRoute"
import { GuestRoute } from "./GuestRoute"

const LoginPage = lazy(() =>
  import("@/features/auth/LoginPage").then((m) => ({ default: m.LoginPage })),
)
const OptimizerPage = lazy(() =>
  import("@/features/optimizer/OptimizerPage").then((m) => ({
    default: m.OptimizerPage,
  })),
)
const InsightsRecommendationsPage = lazy(() =>
  import("@/features/insights/InsightsRecommendationsPage").then((m) => ({
    default: m.InsightsRecommendationsPage,
  })),
)
const NotificationsPage = lazy(() =>
  import("@/features/notifications/NotificationsPage").then((m) => ({
    default: m.NotificationsPage,
  })),
)
const SettingsPage = lazy(() =>
  import("@/features/settings/SettingsPage").then((m) => ({
    default: m.SettingsPage,
  })),
)
const DealFinderPage = lazy(() =>
  import("@/features/deal-finder/DealFinderPage").then((m) => ({
    default: m.DealFinderPage,
  })),
)

function SuspenseFallback() {
  return (
    <div className="flex items-center justify-center py-20">
      <span className="size-6 animate-pulse rounded-full bg-violet-400/50" />
    </div>
  )
}

function RouteErrorBoundary() {
  return <ErrorBoundary><></></ErrorBoundary>
}

export const router = createBrowserRouter([
  {
    element: <GuestRoute />,
    children: [
      {
        path: ROUTES.LOGIN,
        element: (
          <Suspense fallback={<SuspenseFallback />}>
            <LoginPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    element: <ProtectedRoute />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <Navigate to={ROUTES.OPTIMIZER} replace />,
          },
          {
            path: "optimizer",
            element: (
              <Suspense fallback={<SuspenseFallback />}>
                <OptimizerPage />
              </Suspense>
            ),
          },
          {
            path: "insights",
            element: (
              <Suspense fallback={<SuspenseFallback />}>
                <InsightsRecommendationsPage />
              </Suspense>
            ),
          },
          {
            path: "deal-finder",
            element: (
              <Suspense fallback={<SuspenseFallback />}>
                <DealFinderPage />
              </Suspense>
            ),
          },
          {
            path: "notifications",
            element: (
              <Suspense fallback={<SuspenseFallback />}>
                <NotificationsPage />
              </Suspense>
            ),
          },
          {
            path: "settings",
            element: (
              <Suspense fallback={<SuspenseFallback />}>
                <SettingsPage />
              </Suspense>
            ),
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
])
