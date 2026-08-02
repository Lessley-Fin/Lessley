import { describe, it, expect, beforeEach } from "vitest"
import { screen } from "@testing-library/react"
import { render } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { useAuthStore } from "@/features/auth/store"
import { ProtectedRoute } from "./ProtectedRoute"

function TestApp({ initialPath = "/" }: { initialPath?: string }) {
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<div>Protected Content</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      username: "User",
      userId: "",
      email: "",
    })
  })

  it("redirects to /login when not authenticated", () => {
    render(<TestApp />)
    expect(screen.getByText("Login Page")).toBeInTheDocument()
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument()
  })

  it("renders children when authenticated", () => {
    useAuthStore.setState({ isAuthenticated: true, accessToken: "valid" })
    render(<TestApp />)
    expect(screen.getByText("Protected Content")).toBeInTheDocument()
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument()
  })
})
