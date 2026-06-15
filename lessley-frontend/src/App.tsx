import { useCallback, useEffect, useState } from "react"

import { LoginPage } from "@/features/auth/LoginPage"
import { InsightsRecommendationsPage } from "@/features/insights/InsightsRecommendationsPage"
import { NotificationsPage } from "@/features/notifications/NotificationsPage"
import { getUnreadCount } from "@/features/notifications/notificationsStore"
import { OptimizerPage } from "@/features/optimizer/OptimizerPage"
import { SettingsPage } from "@/features/settings/SettingsPage"
import { MainShell, type MainTab } from "@/features/shell/MainShell"
import { getMyProfile } from "@/lib/api"

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/")
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4)
  return atob(padded)
}

function getEmailFromAccessToken(accessToken: string) {
  try {
    const parts = accessToken.split(".")
    if (parts.length < 2) return ""
    const payload = JSON.parse(decodeBase64Url(parts[1])) as Record<string, unknown>
    const claimCandidates = [
      payload.email,
      payload.upn,
      payload.preferred_username,
      payload["http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"],
    ]
    const match = claimCandidates.find((item) => typeof item === "string" && item.includes("@"))
    return typeof match === "string" ? match.trim().toLowerCase() : ""
  } catch {
    return ""
  }
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => localStorage.getItem("lessley_poc_session") === "active"
  )
  const [username, setUsername] = useState(() => localStorage.getItem("lessley_username") ?? "User")
  const [userId, setUserId] = useState(() => localStorage.getItem("lessley_user_id") ?? "")
  const [email, setEmail] = useState(() => localStorage.getItem("lessley_user_email") ?? "")
  const [mainTab, setMainTab] = useState<MainTab>("optimizer")
  const [showNotifications, setShowNotifications] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [unreadCount, setUnreadCount] = useState(() => getUnreadCount())

  const refreshUnreadCount = useCallback(() => {
    setUnreadCount(getUnreadCount())
  }, [])

  useEffect(() => {
    if (!isAuthenticated || (userId && email)) return

    const accessToken = localStorage.getItem("lessley_access_token")
    if (!accessToken) return

    if (!email) {
      const tokenEmail = getEmailFromAccessToken(accessToken)
      if (tokenEmail) {
        setEmail(tokenEmail)
        localStorage.setItem("lessley_user_email", tokenEmail)
      }
    }

    if (userId) return

    let isMounted = true
    void getMyProfile(accessToken)
      .then((profile) => {
        if (!isMounted) return
        setUserId(profile.userId)
        setUsername(profile.userName)
        if (profile.email) {
          setEmail(profile.email)
          localStorage.setItem("lessley_user_email", profile.email)
        }
        localStorage.setItem("lessley_user_id", profile.userId)
        localStorage.setItem("lessley_username", profile.userName)
      })
      .catch(() => {
        // Keep current state; shell will still render.
      })

    return () => {
      isMounted = false
    }
  }, [isAuthenticated, userId, email])

  const handleLogout = () => {
    localStorage.removeItem("lessley_poc_session")
    localStorage.removeItem("lessley_access_token")
    localStorage.removeItem("lessley_refresh_token")
    localStorage.removeItem("lessley_username")
    localStorage.removeItem("lessley_user_id")
    localStorage.removeItem("lessley_user_email")
    setIsAuthenticated(false)
    setUsername("User")
    setUserId("")
    setEmail("")
    setMainTab("optimizer")
    setShowNotifications(false)
    setShowSettings(false)
    setUnreadCount(0)
  }

  const openMainTab = (tab: MainTab) => {
    setMainTab(tab)
    setShowNotifications(false)
    setShowSettings(false)
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        onSuccess={() => {
          setUsername(localStorage.getItem("lessley_username") ?? "User")
          setUserId(localStorage.getItem("lessley_user_id") ?? "")
          setEmail(localStorage.getItem("lessley_user_email") ?? "")
          setIsAuthenticated(true)
        }}
      />
    )
  }

  return (
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
          onBack={() => setShowNotifications(false)}
          onReadStateChange={refreshUnreadCount}
        />
      ) : showSettings ? (
        <SettingsPage onBack={() => setShowSettings(false)} />
      ) : mainTab === "optimizer" ? (
        <OptimizerPage />
      ) : (
        <InsightsRecommendationsPage username={username} userId={userId} email={email} />
      )}
    </MainShell>
  )
}

export default App
