import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
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

/** Answers the connection probe with `connected`, and the delete with `deleteResult`. */
function stubApi(connected: boolean, deleteResult: "ok" | Error = "ok") {
  mockApiFetch.mockImplementation((path: string, options?: RequestInit) => {
    if (options?.method === "DELETE") {
      return deleteResult === "ok" ? Promise.resolve(null) : Promise.reject(deleteResult)
    }
    if (path.includes("open-finance/accounts")) {
      return Promise.resolve({ data: connected ? [{ id: "acc-1" }] : [] })
    }
    return Promise.resolve(null)
  })
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

  render(<DeleteAccountDialog open onOpenChange={onOpenChange} username="tester" />, { wrapper })
  return { onOpenChange, queryClient }
}

async function fillCredentials(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(t("settings.deleteAccount.passwordLabel")), "correct-horse")
  await user.click(screen.getByRole("button", { name: t("common.confirm") }))
}

describe("DeleteAccountDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ status: "authenticated", isAuthenticated: true, username: "tester" })
  })

  it("walks options → credentials → confirm and sends the choice to close the connection", async () => {
    const user = userEvent.setup()
    stubApi(true)
    const { onOpenChange } = renderDialog()

    await screen.findByText(t("settings.deleteAccount.optionWithConnection"))
    await user.click(screen.getByText(t("settings.deleteAccount.optionWithConnection")))
    await user.click(screen.getByRole("button", { name: t("common.confirm") }))

    // The identifier arrives prefilled, so only the password has to be typed.
    expect(screen.getByLabelText(t("settings.deleteAccount.identifierLabel"))).toHaveValue("tester")
    await fillCredentials(user)

    await user.click(screen.getByRole("button", { name: t("settings.deleteAccount.confirmButton") }))

    await waitFor(() =>
      expect(mockApiFetch).toHaveBeenCalledWith(
        "/api/v1/User/me",
        expect.objectContaining({
          method: "DELETE",
          body: JSON.stringify({
            userNameOrEmail: "tester",
            password: "correct-horse",
            closeOpenFinanceConnection: true,
          }),
        }),
      ),
    )
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
  })

  it("skips the connection choice when there is no connection to close", async () => {
    const user = userEvent.setup()
    stubApi(false)
    renderDialog()

    await screen.findByLabelText(t("settings.deleteAccount.identifierLabel"))
    expect(
      screen.queryByText(t("settings.deleteAccount.optionWithConnection")),
    ).not.toBeInTheDocument()

    await fillCredentials(user)
    await user.click(screen.getByRole("button", { name: t("settings.deleteAccount.confirmButton") }))

    await waitFor(() =>
      expect(mockApiFetch).toHaveBeenCalledWith(
        "/api/v1/User/me",
        expect.objectContaining({
          body: JSON.stringify({
            userNameOrEmail: "tester",
            password: "correct-horse",
            closeOpenFinanceConnection: false,
          }),
        }),
      ),
    )
  })

  it("keeps the dialog open on a rejected password and says nothing was deleted", async () => {
    const user = userEvent.setup()
    stubApi(false, new ApiError("Invalid credentials", 400))
    const { onOpenChange } = renderDialog()

    await screen.findByLabelText(t("settings.deleteAccount.identifierLabel"))
    await fillCredentials(user)
    await user.click(screen.getByRole("button", { name: t("settings.deleteAccount.confirmButton") }))

    // Back on the credentials step with the error, because that is what a retry must change.
    expect(await screen.findByText(t("settings.deleteAccount.invalidCredentials"))).toBeInTheDocument()
    expect(screen.getByLabelText(t("settings.deleteAccount.identifierLabel"))).toBeInTheDocument()
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
  })

  it("reports a failed bank disconnect as nothing having been deleted", async () => {
    const user = userEvent.setup()
    stubApi(false, new ApiError("bad gateway", 502))
    renderDialog()

    await screen.findByLabelText(t("settings.deleteAccount.identifierLabel"))
    await fillCredentials(user)
    await user.click(screen.getByRole("button", { name: t("settings.deleteAccount.confirmButton") }))

    expect(
      await screen.findByText(t("settings.deleteAccount.connectionCloseFailed")),
    ).toBeInTheDocument()
  })

  it("clears the cached data and signs out once the account is gone", async () => {
    const user = userEvent.setup()
    stubApi(false)
    const { queryClient } = renderDialog()
    // Asserted on the call, not on an empty cache: the dialog's own connection query is still
    // mounted and re-registers itself the moment the cache is dropped.
    const clear = vi.spyOn(queryClient, "clear")

    await screen.findByLabelText(t("settings.deleteAccount.identifierLabel"))
    await fillCredentials(user)
    await user.click(screen.getByRole("button", { name: t("settings.deleteAccount.confirmButton") }))

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false))
    expect(clear).toHaveBeenCalled()
  })
})
