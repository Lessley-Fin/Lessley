import { useTranslation } from "react-i18next"

import logoUrl from "../../../assets/logo-with-name.svg"
import { AboutLessleyDialog } from "@/components/shared/AboutLessleyDialog"
import { LoginForm } from "./components/LoginForm"

export function LoginPage() {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-full flex-col justify-center px-6 py-10">
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <img src={logoUrl} alt={t("common.appName")} className="mb-4 size-24" />
          <h1 className="text-3xl font-bold tracking-tight">{t("auth.login.welcomeBack")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("auth.login.tagline")}</p>
          <div className="mt-4">
            <AboutLessleyDialog />
          </div>
        </div>
        <LoginForm />
      </div>
    </div>
  )
}
