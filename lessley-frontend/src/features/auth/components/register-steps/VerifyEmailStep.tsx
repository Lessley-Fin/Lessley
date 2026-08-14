import { useTranslation } from "react-i18next"

import type { VerificationPolicy } from "../../api"

import { CodeEntryForm } from "../CodeEntryForm"

interface VerifyEmailStepProps {
  email: string
  isVerifying: boolean
  isResending: boolean
  error?: string
  policy?: VerificationPolicy
  onVerify: (code: string) => void
  onResend: () => void
}

/**
 * Sits between the account details and the preference steps. Until this passes, the account
 * genuinely does not exist — nothing has been written to Identity yet.
 */
export function VerifyEmailStep({
  email,
  isVerifying,
  isResending,
  error,
  policy,
  onVerify,
  onResend,
}: VerifyEmailStepProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h1 className="text-xl font-bold">{t("auth.register.verifyEmail.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("auth.register.verifyEmail.subtitle")}</p>
      </div>
      <CodeEntryForm
        email={email}
        isWorking={isVerifying}
        isResending={isResending}
        error={error}
        policy={policy}
        onSubmit={onVerify}
        onResend={onResend}
      />
    </div>
  )
}
