import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { ArrowLeft } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { StepIndicator } from "@/components/shared/StepIndicator"
import { Form } from "@/components/ui/form"
import { ROUTES } from "@/lib/routes"
import { loginWithGateway, registerWithGateway } from "../api"
import { registerSchema, type RegisterValues } from "../schemas"
import { useApplyAuthProfile } from "../usePostAuth"
import { AccountStep } from "./register-steps/AccountStep"
import { BankingStep } from "./register-steps/BankingStep"
import { ClubsStep } from "./register-steps/ClubsStep"

const STEPS = ["Account", "Clubs", "Banking"]

export function RegisterWizard() {
  const [step, setStep] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const navigate = useNavigate()
  const applyAuthProfile = useApplyAuthProfile()

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { userName: "", email: "", password: "", verifyPassword: "", clubs: [] },
  })

  const serverError = form.formState.errors.root?.message

  async function handleContinueFromAccount() {
    const valid = await form.trigger(["userName", "email", "password", "verifyPassword"])
    if (valid) setStep(1)
  }

  // Real account creation happens here, once clubs are picked — BankingStep needs an
  // authenticated session for its own connect-bank call, so registration can't wait any longer.
  async function handleContinueFromClubs() {
    const values = form.getValues()
    setIsSubmitting(true)
    try {
      await registerWithGateway({
        userName: values.userName,
        email: values.email,
        password: values.password,
        clubs: values.clubs?.length ? values.clubs : undefined,
      })
      const data = await loginWithGateway({ userName: values.userName, password: values.password })
      await applyAuthProfile({ userName: data.userName ?? values.userName, email: data.email ?? values.email })
      setStep(2)
    } catch (error) {
      form.setError("root", {
        message: error instanceof Error ? error.message : "Registration failed. Please try again.",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleBack() {
    if (step === 0) navigate(ROUTES.LOGIN)
    else setStep(step - 1)
  }

  function handleFinish() {
    navigate(ROUTES.OPTIMIZER, { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col px-6 py-8">
      <button
        type="button"
        onClick={handleBack}
        className="mb-6 flex items-center gap-2 text-sm font-medium text-muted-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden /> Back
      </button>
      <div className="mx-auto w-full max-w-sm">
        <StepIndicator steps={STEPS} currentIndex={step} />
        <Form {...form}>
          {step === 0 ? <AccountStep form={form} onContinue={handleContinueFromAccount} /> : null}
          {step === 1 ? (
            <ClubsStep
              form={form}
              isLoading={isSubmitting}
              serverError={serverError}
              onContinue={handleContinueFromClubs}
            />
          ) : null}
          {step === 2 ? <BankingStep onFinish={handleFinish} /> : null}
        </Form>
      </div>
    </div>
  )
}
