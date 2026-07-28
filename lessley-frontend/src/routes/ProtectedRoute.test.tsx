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
      status: "unauthenticated",
      isAuthenticated: false,
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
    useAuthStore.setState({ status: "authenticated", isAuthenticated: true })
    render(<TestApp />)
    expect(screen.getByText("Protected Content")).toBeInTheDocument()
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument()
  })

  it("renders neither while the auth probe is loading", () => {
    useAuthStore.setState({ status: "loading", isAuthenticated: false })
    render(<TestApp />)
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument()
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument()
  })
})
