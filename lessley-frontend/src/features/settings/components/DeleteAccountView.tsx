import { useState } from "react"
import { Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { DeleteAccountDialog } from "./DeleteAccountDialog"

export function DeleteAccountView() {
  const { t } = useTranslation()
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <div className="space-y-3 rounded-3xl bg-card p-5 shadow-[var(--shadow-card)]">
      <Trash2 className="size-6 text-destructive" aria-hidden />
      <p className="font-bold">{t("settings.deleteAccount.title")}</p>
      <p className="text-sm text-muted-foreground">{t("settings.deleteAccount.warning")}</p>
      <Button type="button" variant="destructive" size="xl" onClick={() => setDialogOpen(true)}>
        {t("settings.deleteAccount.deleteButton")}
      </Button>

      <DeleteAccountDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  )
}
