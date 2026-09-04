import { useState } from "react"
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
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { useDeleteAccount } from "@/features/user/hooks"
import { ApiError } from "@/lib/api-client"
import { ROUTES } from "@/lib/routes"

interface DeleteAccountDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function DeleteAccountDialog({ open, onOpenChange }: DeleteAccountDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {/* The flow lives in its own component so closing the dialog unmounts it: a cancelled
            attempt takes its half-typed confirmation with it, and the next attempt is asked for
            a freshly generated code rather than the one already on screen. */}
        <DeleteAccountFlow onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  )
}

function DeleteAccountFlow({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const deleteAccount = useDeleteAccount()

  // Generated once per opening of the dialog. Nothing about it is sent anywhere: it exists to
  // make deletion a deliberate act of typing rather than a click someone can land on by muscle
  // memory, and the account being deleted comes from the session either way.
  const [confirmationCode] = useState(generateConfirmationCode)
  const [typedCode, setTypedCode] = useState("")

  const codeMatches = typedCode.trim().toUpperCase() === confirmationCode

  function handleConfirm() {
    deleteAccount.mutate(undefined, {
      onSuccess: () => {
        onClose()
        navigate(ROUTES.LOGIN, { replace: true })
      },
    })
  }

  const errorMessage = describeError(deleteAccount.error, t)

  return (
    <>
      <DialogHeader>
        <DialogTitle>{t("settings.deleteAccount.title")}</DialogTitle>
        <DialogDescription>{t("settings.deleteAccount.confirmTitle")}</DialogDescription>
      </DialogHeader>

      <DialogBody>
        <div className="space-y-3">
          <ErrorAlert message={errorMessage} />

          <p className="text-sm text-foreground">{t("settings.deleteAccount.confirmBody")}</p>

          <p
            id="delete-account-code-value"
            dir="ltr"
            className="rounded-2xl bg-secondary/60 py-2 text-center font-mono text-lg font-bold tracking-[0.3em]"
          >
            {confirmationCode}
          </p>

          <div className="space-y-1.5">
            <Label htmlFor="delete-account-code">
              {t("settings.deleteAccount.confirmCodeLabel")}
            </Label>
            <Input
              id="delete-account-code"
              dir="ltr"
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              aria-describedby="delete-account-code-value"
              value={typedCode}
              onChange={(e) => setTypedCode(e.target.value)}
            />
          </div>
        </div>
      </DialogBody>

      <DialogFooter>
        <Button
          type="button"
          variant="destructive"
          size="xl"
          disabled={!codeMatches || deleteAccount.isPending}
          onClick={handleConfirm}
        >
          {deleteAccount.isPending
            ? t("settings.deleteAccount.deleting")
            : t("settings.deleteAccount.confirmButton")}
        </Button>

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

// No O/0 or I/1: the code only works as a speed bump if it can be read off the screen and typed
// back without a second guess. 32 characters divides 256 exactly, so the modulo below is unbiased.
const CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
const CODE_LENGTH = 6

function generateConfirmationCode(): string {
  const bytes = new Uint8Array(CODE_LENGTH)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (byte) => CODE_ALPHABET[byte % CODE_ALPHABET.length]).join("")
}

/** Status, not message text — the server's copy is untranslated and the codes are stable. */
function describeError(error: unknown, t: (key: string) => string): string | null {
  if (!error) return null
  if (error instanceof ApiError && error.status === 502) {
    return t("settings.deleteAccount.connectionCloseFailed")
  }
  return t("settings.deleteAccount.genericError")
}
