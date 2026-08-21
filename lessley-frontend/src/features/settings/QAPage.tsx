import { useTranslation } from "react-i18next"

import { QAView } from "./components/QAView"

export function QAPage() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("settings.menu.qaTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("settings.menu.qaDesc")}</p>
      </div>

      <div className="no-scrollbar min-h-0 flex-1 overflow-y-auto pb-2">
        <QAView />
      </div>
    </div>
  )
}
