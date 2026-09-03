import { useState } from "react"
import { Check } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { useHasConnection } from "@/features/insights/hooks"
import { useDeleteAccount } from "@/features/user/hooks"
import { ApiError } from "@/lib/api-client"
import { ROUTES } from "@/lib/routes"
import { cn } from "@/lib/utils"

type Step = "options" | "credentials" | "confirm"

interface DeleteAccountDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Prefilled into the identifier field so the user confirms rather than guesses. */
  username: string
}

export function DeleteAccountDialog({ open, onOpenChange, username }: DeleteAccountDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {/* The flow lives in its own component so closing the dialog unmounts it: a cancelled
            attempt takes its typed password and half-made choice with it, with no reset to
            remember to write. */}
        <DeleteAccountFlow username={username} onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  )
}

function DeleteAccountFlow({ username, onClose }: { username: string; onClose: () => void }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: isConnected } = useHasConnection()
  const deleteAccount = useDeleteAccount()

  // With no bank link there is nothing to decide, so the choice step would be a dead click.
  const offersConnectionChoice = isConnected === true

  const [chosenStep, setChosenStep] = useState<Step | null>(null)
  const [closeConnection, setCloseConnection] = useState(false)
  const [identifier, setIdentifier] = useState(username)
  const [password, setPassword] = useState("")

  // Null until the connection status lands. Opening on a guess and correcting it on arrival
  // would move the dialog out from under someone already typing.
  const step: Step | null =
    chosenStep ?? (isConnected === undefined ? null : isConnected ? "options" : "credentials")

  function handleConfirm() {
    deleteAccount.mutate(
      {
        userNameOrEmail: identifier.trim(),
        password,
        closeOpenFinanceConnection: offersConnectionChoice && closeConnection,
      },
      {
        onSuccess: () => {
          onClose()
          navigate(ROUTES.LOGIN, { replace: true })
        },
        // The credentials are what a retry has to change, so send the user back to them.
        onError: () => setChosenStep("credentials"),
      },
    )
  }

  const errorMessage = describeError(deleteAccount.error, t)
  const canSubmitCredentials = identifier.trim().length > 0 && password.length > 0

  return (
    <>
      <DialogHeader>
        <DialogTitle>{t("settings.deleteAccount.title")}</DialogTitle>
        <DialogDescription>
          {step === "options"
            ? t("settings.deleteAccount.optionsTitle")
            : step === "credentials"
              ? t("settings.deleteAccount.credentialsTitle")
              : step === "confirm"
                ? t("settings.deleteAccount.confirmTitle")
                : t("settings.deleteAccount.warning")}
        </DialogDescription>
      </DialogHeader>

      <DialogBody>
        {step === null ? (
          <p className="text-sm text-muted-foreground">{t("settings.page.loading")}</p>
        ) : null}

        {step === "options" ? (
          <div className="space-y-2">
            <ChoiceButton
              selected={!closeConnection}
              title={t("settings.deleteAccount.optionLessleyOnly")}
              description={t("settings.deleteAccount.optionLessleyOnlyDesc")}
              onSelect={() => setCloseConnection(false)}
            />
            <ChoiceButton
              selected={closeConnection}
              title={t("settings.deleteAccount.optionWithConnection")}
              description={t("settings.deleteAccount.optionWithConnectionDesc")}
              onSelect={() => setCloseConnection(true)}
            />
          </div>
        ) : null}

        {step === "credentials" ? (
          <div className="space-y-3">
            <ErrorAlert message={errorMessage} />
            <div className="space-y-1.5">
              <Label htmlFor="delete-account-identifier">
                {t("settings.deleteAccount.identifierLabel")}
              </Label>
              <Input
                id="delete-account-identifier"
                dir="ltr"
                autoComplete="username"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="delete-account-password">
                {t("settings.deleteAccount.passwordLabel")}
              </Label>
              <PasswordInput
                id="delete-account-password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>
        ) : null}

        {step === "confirm" ? (
          <div className="space-y-3">
            <p className="text-sm text-foreground">{t("settings.deleteAccount.confirmBody")}</p>
            <p className="text-sm text-muted-foreground">
              {offersConnectionChoice && closeConnection
                ? t("settings.deleteAccount.confirmWithConnection")
                : t("settings.deleteAccount.confirmWithoutConnection")}
            </p>
          </div>
        ) : null}
      </DialogBody>

      <DialogFooter>
        {step === "options" ? (
          <Button type="button" variant="hero" size="xl" onClick={() => setChosenStep("credentials")}>
            {t("common.confirm")}
          </Button>
        ) : null}

        {step === "credentials" ? (
          <Button
            type="button"
            variant="hero"
            size="xl"
            disabled={!canSubmitCredentials}
            onClick={() => setChosenStep("confirm")}
          >
            {t("common.confirm")}
          </Button>
        ) : null}

        {step === "confirm" ? (
          <Button
            type="button"
            variant="destructive"
            size="xl"
            disabled={deleteAccount.isPending}
            onClick={handleConfirm}
          >
            {deleteAccount.isPending
              ? t("settings.deleteAccount.deleting")
              : t("settings.deleteAccount.confirmButton")}
          </Button>
        ) : null}

        <Button
          type="button"
          variant="ghost"
          size="xl"
          disabled={deleteAccount.isPending}
          onClick={onClose}
        >
          {t("common.cancel")}
        </Button>
      </DialogFooter>
    </>
  )
}

interface ChoiceButtonProps {
  selected: boolean
  title: string
  description: string
  onSelect: () => void
}

function ChoiceButton({ selected, title, description, onSelect }: ChoiceButtonProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "flex w-full items-start gap-3 rounded-2xl p-3 text-start transition-colors",
        selected ? "bg-accent text-accent-foreground" : "bg-secondary/60 hover:bg-accent/60",
      )}
    >
      <div className="flex-1">
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      {selected ? <Check className="mt-0.5 size-4 shrink-0" aria-hidden /> : null}
    </button>
  )
}

/** Status, not message text — the server's copy is untranslated and the codes are stable. */
function describeError(error: unknown, t: (key: string) => string): string | null {
  if (!error) return null
  if (error instanceof ApiError) {
    if (error.status === 400) return t("settings.deleteAccount.invalidCredentials")
    if (error.status === 423) return t("settings.deleteAccount.lockedOut")
    if (error.status === 502) return t("settings.deleteAccount.connectionCloseFailed")
  }
  return t("settings.deleteAccount.genericError")
}
