import { useEffect, useMemo, useState } from "react"

import { LoginPage } from "@/features/auth/LoginPage"
import { DashboardPage } from "@/features/dashboard/DashboardPage"
import { initialFeedback } from "@/features/feedback/mockFeedback"
import { getMyProfile } from "@/lib/api"
import type { FeedbackItem } from "@/lib/types"

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => localStorage.getItem("lessley_poc_session") === "active"
  )
  const [username, setUsername] = useState(() => localStorage.getItem("lessley_username") ?? "User")
  const [userId, setUserId] = useState(() => localStorage.getItem("lessley_user_id") ?? "")
  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>(initialFeedback)

  const sortedFeedback = useMemo(
    () => [...feedbackItems].reverse(),
    [feedbackItems]
  )

  useEffect(() => {
    if (!isAuthenticated || userId) return

    const accessToken = localStorage.getItem("lessley_access_token")
    if (!accessToken) return

    let isMounted = true
    void getMyProfile(accessToken)
      .then((profile) => {
        if (!isMounted) return
        setUserId(profile.userId)
        setUsername(profile.userName)
        localStorage.setItem("lessley_user_id", profile.userId)
        localStorage.setItem("lessley_username", profile.userName)
      })
      .catch(() => {
        // Keep current state; dashboard will still render.
      })

    return () => {
      isMounted = false
    }
  }, [isAuthenticated, userId])

  const handleLogout = () => {
    localStorage.removeItem("lessley_poc_session")
    localStorage.removeItem("lessley_access_token")
    localStorage.removeItem("lessley_refresh_token")
    localStorage.removeItem("lessley_username")
    localStorage.removeItem("lessley_user_id")
    setIsAuthenticated(false)
    setUsername("User")
    setUserId("")
  }

  const handleCreateFeedback = (item: FeedbackItem) => {
    setFeedbackItems((prev) => [...prev, item])
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        onSuccess={() => {
          setUsername(localStorage.getItem("lessley_username") ?? "User")
          setUserId(localStorage.getItem("lessley_user_id") ?? "")
          setIsAuthenticated(true)
        }}
      />
    )
  }

  return (
    <DashboardPage
      username={username}
      userId={userId}
      feedbackItems={sortedFeedback}
      onCreateFeedback={handleCreateFeedback}
      onLogout={handleLogout}
    />
  )
}

export default App
