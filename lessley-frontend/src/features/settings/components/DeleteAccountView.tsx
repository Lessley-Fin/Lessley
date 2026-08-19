import { useState } from "react"
import { Trash2 } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { useAuthStore } from "@/features/auth/store"
import { useDeleteMyAccount } from "@/features/user/hooks"
import { ROUTES } from "@/lib/routes"

interface DeleteAccountViewProps {
  username: string
}

export function DeleteAccountView({ username }: DeleteAccountViewProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const deleteAccount = useDeleteMyAccount()

  async function handleConfirmDelete() {
    await deleteAccount.mutateAsync()
    useAuthStore.getState().logout()
    navigate(ROUTES.LOGIN, { replace: true })
  }

  return (
    <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <p className="font-bold">{t("settings.deleteAccount.signedInAs", { username })}</p>
      <p className="text-sm text-muted-foreground">{t("settings.deleteAccount.notice")}</p>
      {deleteAccount.isError ? (
        <p className="text-sm text-destructive">{t("settings.deleteAccount.error")}</p>
      ) : null}
      <Button type="button" variant="destructive" size="xl" onClick={() => setConfirmOpen(true)}>
        <Trash2 className="size-4" aria-hidden />
        {t("settings.deleteAccount.deleteButton")}
      </Button>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("settings.deleteAccount.confirmTitle")}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">{t("settings.deleteAccount.confirmBody")}</p>
          <DialogFooter>
            <Button
              type="button"
              variant="destructive"
              size="xl"
              onClick={handleConfirmDelete}
              disabled={deleteAccount.isPending}
            >
              {deleteAccount.isPending ? t("settings.deleteAccount.deleting") : t("settings.deleteAccount.confirmButton")}
            </Button>
            <Button
              type="button"
              variant="pill"
              size="xl"
              onClick={() => setConfirmOpen(false)}
              disabled={deleteAccount.isPending}
            >
              {t("common.cancel")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
