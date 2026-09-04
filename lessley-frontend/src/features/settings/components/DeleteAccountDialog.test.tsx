import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

import { useAuthStore } from "@/features/auth/store"
import i18n from "@/lib/i18n/config"
import { DeleteAccountDialog } from "./DeleteAccountDialog"

// The real ApiError is kept: the dialog maps its `status` to the message the user sees.
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>()
  return { ...actual, apiFetch: vi.fn() }
})
vi.mock("@/lib/auth", () => ({ logoutRequest: vi.fn().mockResolvedValue(undefined) }))

const { apiFetch, ApiError } = await import("@/lib/api-client")
const mockApiFetch = apiFetch as Mock

const t = (key: string) => i18n.t(key)

function stubDelete(result: "ok" | Error = "ok") {
  mockApiFetch.mockImplementation(() =>
    result === "ok" ? Promise.resolve(null) : Promise.reject(result),
  )
}

function renderDialog() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const onOpenChange = vi.fn()

  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  )

  render(<DeleteAccountDialog open onOpenChange={onOpenChange} />, { wrapper })
  return { onOpenChange, queryClient }
}

/** The generated code is the only 6-character all-caps token on screen. */
function shownCode() {
  return screen.getByText(/^[A-Z2-9]{6}$/).textContent as string
}

function deleteButton() {
  return screen.getByRole("button", { name: t("settings.deleteAccount.confirmButton") })
}

async function typeTheCode(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(t("settings.deleteAccount.confirmCodeLabel")), shownCode())
}

describe("DeleteAccountDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ status: "authenticated", isAuthenticated: true, username: "tester" })
  })

  it("keeps deletion out of reach until the shown code is typed back", async () => {
    const user = userEvent.setup()
    stubDelete()
    renderDialog()

    expect(deleteButton()).toBeDisabled()

    const input = screen.getByLabelText(t("settings.deleteAccount.confirmCodeLabel"))
    await user.type(input, "NOPE12")
    expect(deleteButton()).toBeDisabled()

    await user.clear(input)
    await typeTheCode(user)
    expect(deleteButton()).toBeEnabled()

    // Never sent anywhere: the code is a client-side speed bump, and the code the user typed
    // is not part of the request.
    expect(mockApiFetch).not.toHaveBeenCalled()
  })

  it("deletes with no body at all — the account is the one in the session", async () => {
    const user = userEvent.setup()
    stubDelete()
    const { onOpenChange } = renderDialog()

    await typeTheCode(user)
    await user.click(deleteButton())

    await waitFor(() =>
      expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/User/me", { method: "DELETE" }),
    )
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
  })

  it("asks for a freshly generated code every time the dialog is opened", async () => {
    stubDelete()
    renderDialog()
    const firstCode = shownCode()

    // Unmounting and rendering again is what closing and reopening the dialog does.
    cleanup()
    renderDialog()

    expect(shownCode()).not.toBe(firstCode)
  })

  it("reports a failed bank disconnect as nothing having been deleted", async () => {
    const user = userEvent.setup()
    stubDelete(new ApiError("bad gateway", 502))
    const { onOpenChange } = renderDialog()

    await typeTheCode(user)
    await user.click(deleteButton())

    expect(
      await screen.findByText(t("settings.deleteAccount.connectionCloseFailed")),
    ).toBeInTheDocument()
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
  })

  it("clears the cached data and signs out once the account is gone", async () => {
    const user = userEvent.setup()
    stubDelete()
    const { queryClient } = renderDialog()
    const clear = vi.spyOn(queryClient, "clear")

    await typeTheCode(user)
    await user.click(deleteButton())

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false))
    expect(clear).toHaveBeenCalled()
  })
})
