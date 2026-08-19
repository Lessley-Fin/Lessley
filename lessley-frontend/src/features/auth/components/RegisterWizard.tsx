import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { ArrowLeft } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { StepIndicator } from "@/components/shared/StepIndicator"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Form } from "@/components/ui/form"
import { useAuthStore } from "@/features/auth/store"
import { ROUTES } from "@/lib/routes"
import type { VerificationPolicy } from "../api"
import {
  completeRegistration,
  resendRegistrationCode,
  startRegistration,
  verifyRegistrationEmail,
} from "../api"
import { registerSchema, type RegisterValues } from "../schemas"
import { useApplyAuthProfile } from "../usePostAuth"
import { AccountStep } from "./register-steps/AccountStep"
import { BankingStep } from "./register-steps/BankingStep"
import { ClubsStep } from "./register-steps/ClubsStep"
import { MatchLevelStep } from "./register-steps/MatchLevelStep"
import { VerifyEmailStep } from "./register-steps/VerifyEmailStep"

const STEP = {
  ACCOUNT: 0,
  VERIFY_EMAIL: 1,
  CLUBS: 2,
  MATCH_LEVEL: 3,
  BANKING: 4,
} as const

export function RegisterWizard() {
  const { t } = useTranslation()
  const STEPS = [
    t("auth.register.stepAccount"),
    t("auth.register.stepVerify"),
    t("auth.register.stepClubs"),
    t("auth.register.stepMatchLevel"),
    t("auth.register.stepBanking"),
  ]
  const [step, setStep] = useState<number>(STEP.ACCOUNT)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [codeError, setCodeError] = useState<string | undefined>()
  // Handle for the pending registration on the server. Nothing exists under the user's name
  // until the final `completeRegistration` call, so losing this (refresh, back to login) simply
  // means starting over — which is exactly the intended behaviour.
  const [registrationToken, setRegistrationToken] = useState("")
  const [policy, setPolicy] = useState<VerificationPolicy | undefined>()
  const [showWelcome, setShowWelcome] = useState(false)
  const navigate = useNavigate()
  const applyAuthProfile = useApplyAuthProfile()

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      userName: "",
      email: "",
      password: "",
      verifyPassword: "",
      clubs: [],
      matchLevel: "Medium",
    },
  })

  const serverError = form.formState.errors.root?.message

  function reportError(error: unknown, fallbackKey: string) {
    form.setError("root", {
      message: error instanceof Error ? error.message : t(fallbackKey),
    })
  }

  // Reserves the username/email and sends the verification code. Still creates no account.
  async function handleContinueFromAccount() {
    const valid = await form.trigger(["userName", "email", "password", "verifyPassword"])
    if (!valid) return

    const values = form.getValues()
    setIsSubmitting(true)
    form.clearErrors("root")
    try {
      const started = await startRegistration({
        userName: values.userName,
        email: values.email,
        password: values.password,
      })
      setRegistrationToken(started.registrationToken)
      setPolicy(started.policy)
      setCodeError(undefined)
      setStep(STEP.VERIFY_EMAIL)
    } catch (error) {
      reportError(error, "auth.register.registrationFailed")
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleVerifyEmail(code: string) {
    setIsSubmitting(true)
    setCodeError(undefined)
    try {
      await verifyRegistrationEmail({ registrationToken, code })
      setStep(STEP.CLUBS)
    } catch (error) {
      setCodeError(error instanceof Error ? error.message : t("auth.code.verifyFailed"))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleResendCode() {
    setIsResending(true)
    setCodeError(undefined)
    try {
      const { policy: codePolicy } = await resendRegistrationCode({ registrationToken })
      setPolicy(codePolicy)
    } catch (error) {
      setCodeError(error instanceof Error ? error.message : t("auth.code.resendFailed"))
    } finally {
      setIsResending(false)
    }
  }

  function handleContinueFromClubs() {
    const values = form.getValues()
    if (!values.clubs?.length) {
      form.setError("clubs", { message: t("auth.register.clubs.selectAtLeastOne") })
      return
    }
    setStep(STEP.MATCH_LEVEL)
  }

  // The single call that creates the account, once the email is verified and the preferences
  // are in. It also signs the user in, which BankingStep needs for its connect-bank call.
  async function handleContinueFromMatchLevel() {
    const values = form.getValues()
    setIsSubmitting(true)
    form.clearErrors("root")
    try {
      const profile = await completeRegistration({
        registrationToken,
        clubs: values.clubs?.length ? values.clubs : undefined,
        matchLevel: values.matchLevel,
      })
      // Set before applyAuthProfile flips auth status, so GuestRoute doesn't bounce the user
      // out of /register before the wizard reaches the Banking step.
      useAuthStore.getState().setRegistrationInProgress(true)
      await applyAuthProfile({
        userName: profile.userName ?? values.userName,
        email: profile.email ?? values.email,
      })
      setStep(STEP.BANKING)
      setShowWelcome(true)
    } catch (error) {
      reportError(error, "auth.register.registrationFailed")
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleBack() {
    // Going back past the code step would strand the pending registration, so the account
    // step restarts the flow rather than resuming it.
    if (step === STEP.ACCOUNT) navigate(ROUTES.LOGIN)
    else if (step === STEP.VERIFY_EMAIL) {
      setRegistrationToken("")
      setStep(STEP.ACCOUNT)
    } else setStep(step - 1)
  }

  function handleFinish() {
    useAuthStore.getState().setRegistrationInProgress(false)
    navigate(ROUTES.OPTIMIZER, { replace: true })
  }

  return (
    <div className="flex min-h-full flex-col px-6 py-8">
      <button
        type="button"
        onClick={handleBack}
        className="mb-6 flex items-center gap-2 text-sm font-medium text-muted-foreground"
      >
        <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden /> {t("auth.register.back")}
      </button>
      <div className="mx-auto w-full max-w-sm">
        <StepIndicator steps={STEPS} currentIndex={step} />
        <Form {...form}>
          {step === STEP.ACCOUNT ? (
            <AccountStep form={form} isLoading={isSubmitting} serverError={serverError} onContinue={handleContinueFromAccount} />
          ) : null}
          {step === STEP.VERIFY_EMAIL ? (
            <VerifyEmailStep
              email={form.getValues().email}
              isVerifying={isSubmitting}
              isResending={isResending}
              error={codeError}
              policy={policy}
              onVerify={handleVerifyEmail}
              onResend={handleResendCode}
            />
          ) : null}
          {step === STEP.CLUBS ? <ClubsStep form={form} onContinue={handleContinueFromClubs} /> : null}
          {step === STEP.MATCH_LEVEL ? (
            <MatchLevelStep
              form={form}
              isLoading={isSubmitting}
              serverError={serverError}
              onContinue={handleContinueFromMatchLevel}
            />
          ) : null}
          {step === STEP.BANKING ? <BankingStep onFinish={handleFinish} /> : null}
        </Form>
      </div>

      <Dialog open={showWelcome} onOpenChange={setShowWelcome}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("auth.register.welcome.title", { username: form.getValues().userName })}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">{t("auth.register.welcome.body")}</p>
          <DialogFooter>
            <Button type="button" variant="hero" size="xl" onClick={() => setShowWelcome(false)}>
              {t("auth.register.welcome.continue")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
