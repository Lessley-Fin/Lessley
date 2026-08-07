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
import { AdminRoute } from "./AdminRoute"

const LoginPage = lazy(() =>
  import("@/features/auth/LoginPage").then((m) => ({ default: m.LoginPage })),
)
const RegisterPage = lazy(() =>
  import("@/features/auth/RegisterPage").then((m) => ({ default: m.RegisterPage })),
)
const ForgotPasswordPage = lazy(() =>
  import("@/features/auth/ForgotPasswordPage").then((m) => ({ default: m.ForgotPasswordPage })),
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
const RecommendationsPage = lazy(() =>
  import("@/features/recommendations/RecommendationsPage").then((m) => ({
    default: m.RecommendationsPage,
  })),
)
const HotDealsPage = lazy(() =>
  import("@/features/hot-deals/HotDealsPage").then((m) => ({
    default: m.HotDealsPage,
  })),
)
const AdminPage = lazy(() =>
  import("@/features/admin/AdminPage").then((m) => ({
    default: m.AdminPage,
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
      {
        path: ROUTES.REGISTER,
        element: (
          <Suspense fallback={<SuspenseFallback />}>
            <RegisterPage />
          </Suspense>
        ),
      },
      {
        path: ROUTES.FORGOT_PASSWORD,
        element: (
          <Suspense fallback={<SuspenseFallback />}>
            <ForgotPasswordPage />
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
            path: "recommendations",
            element: (
              <Suspense fallback={<SuspenseFallback />}>
                <RecommendationsPage />
              </Suspense>
            ),
          },
          {
            path: "deal-finder",
            element: <Navigate to={`${ROUTES.OPTIMIZER}?tab=deal-finder`} replace />,
          },
          {
            path: "hot-deals",
            element: (
              <Suspense fallback={<SuspenseFallback />}>
                <HotDealsPage />
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
          {
            element: <AdminRoute />,
            children: [
              {
                path: "admin",
                element: (
                  <Suspense fallback={<SuspenseFallback />}>
                    <AdminPage />
                  </Suspense>
                ),
              },
            ],
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
