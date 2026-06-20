import { useEffect, useState } from "react"

import { AuthGuard } from "@/features/auth/AuthGuard"
import { LoginPage } from "@/features/auth/LoginPage"
import { InsightsRecommendationsPage } from "@/features/insights/InsightsRecommendationsPage"
import { NotificationsPage } from "@/features/notifications/NotificationsPage"
import { useNotifications } from "@/features/notifications/useNotifications"
import { OptimizerPage } from "@/features/optimizer/OptimizerPage"
import { SettingsPage } from "@/features/settings/SettingsPage"
import { MainShell, type MainTab } from "@/features/shell/MainShell"
import { getMyProfile } from "@/lib/api"
import {
  SESSION_KEYS,
  clearSession,
  getAccessToken,
  getEmailFromToken,
  isAuthenticated as checkIsAuthenticated,
  isTokenExpired,
  refreshAccessToken,
} from "@/lib/auth"

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => checkIsAuthenticated())
  const [username, setUsername] = useState(() => localStorage.getItem(SESSION_KEYS.username) ?? "User")
  const [userId, setUserId] = useState(() => localStorage.getItem(SESSION_KEYS.userId) ?? "")
  const [email, setEmail] = useState(() => localStorage.getItem(SESSION_KEYS.email) ?? "")
  const [mainTab, setMainTab] = useState<MainTab>("optimizer")
  const [showNotifications, setShowNotifications] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const { notifications, unreadCount, isLoading, markAllRead } = useNotifications({
    email,
    enabled: isAuthenticated,
  })

  // On mount: if session exists but the access token is expired, attempt a
  // silent refresh. Clears the session and redirects to login on failure.
  useEffect(() => {
    if (!isAuthenticated) return

    const token = getAccessToken()
    if (!token || isTokenExpired(token)) {
      void refreshAccessToken().then((newToken) => {
        if (!newToken) {
          clearSession()
          setIsAuthenticated(false)
          setUsername("User")
          setUserId("")
          setEmail("")
        }
      })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps -- intentionally mount-only

  // Resolve missing profile fields (userId / email) without blocking render.
  useEffect(() => {
    if (!isAuthenticated || (userId && email)) return

    const accessToken = getAccessToken()
    if (!accessToken) return

    if (!email) {
      const tokenEmail = getEmailFromToken(accessToken)
      if (tokenEmail) {
        setEmail(tokenEmail)
        localStorage.setItem(SESSION_KEYS.email, tokenEmail)
      }
    }

    if (userId) return

    let isMounted = true
    void getMyProfile(accessToken)
      .then((profile) => {
        if (!isMounted) return
        setUsername(profile.userName)
        if (profile.email) {
          setUserId(profile.email)
          setEmail(profile.email)
          localStorage.setItem(SESSION_KEYS.email, profile.email)
          localStorage.setItem(SESSION_KEYS.userId, profile.email)
        }
        localStorage.setItem(SESSION_KEYS.username, profile.userName)
      })
      .catch(() => {
        // Keep current state; shell will still render.
      })

    return () => {
      isMounted = false
    }
  }, [isAuthenticated, userId, email])

  const handleLoginSuccess = () => {
    setUsername(localStorage.getItem(SESSION_KEYS.username) ?? "User")
    setUserId(localStorage.getItem(SESSION_KEYS.userId) ?? "")
    setEmail(localStorage.getItem(SESSION_KEYS.email) ?? "")
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    clearSession()
    setIsAuthenticated(false)
    setUsername("User")
    setUserId("")
    setEmail("")
    setMainTab("optimizer")
    setShowNotifications(false)
    setShowSettings(false)
  }

  const openMainTab = (tab: MainTab) => {
    setMainTab(tab)
    setShowNotifications(false)
    setShowSettings(false)
  }

  return (
    <AuthGuard
      isAuthenticated={isAuthenticated}
      fallback={<LoginPage onSuccess={handleLoginSuccess} />}
    >
      <MainShell
        username={username}
        activeTab={mainTab}
        unreadCount={unreadCount}
        onTabChange={openMainTab}
        showNotifications={showNotifications}
        showSettings={showSettings}
        showBottomNav={!showNotifications && !showSettings}
        onOpenNotifications={() => {
          setShowNotifications(true)
          setShowSettings(false)
        }}
        onOpenSettings={() => {
          setShowSettings(true)
          setShowNotifications(false)
        }}
        onLogout={handleLogout}
      >
        {showNotifications ? (
          <NotificationsPage
            notifications={notifications}
            isLoading={isLoading}
            onBack={() => setShowNotifications(false)}
            onMarkAllRead={markAllRead}
          />
        ) : showSettings ? (
          <SettingsPage onBack={() => setShowSettings(false)} />
        ) : mainTab === "optimizer" ? (
          <OptimizerPage />
        ) : (
          <InsightsRecommendationsPage username={username} userId={userId} email={email} />
        )}
      </MainShell>
    </AuthGuard>
  )
}

export default App
