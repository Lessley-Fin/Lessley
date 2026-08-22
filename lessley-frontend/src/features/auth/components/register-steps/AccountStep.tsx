import type { UseFormReturn } from "react-hook-form"
import { Loader2 } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { AboutLessleyDialog } from "@/components/shared/AboutLessleyDialog"
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { PasswordInput } from "@/components/ui/password-input"
import { ROUTES } from "@/lib/routes"
import type { RegisterValues } from "../../schemas"

interface AccountStepProps {
  form: UseFormReturn<RegisterValues>
  // Continuing now hits the server (it reserves the name and sends the code), so this step
  // has to show progress and server-side rejections like "that email is already registered".
  isLoading?: boolean
  serverError?: string
  onContinue: () => void
}

export function AccountStep({ form, isLoading = false, serverError, onContinue }: AccountStepProps) {
  const { t } = useTranslation()
  return (
    <form
      className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]"
      onSubmit={(e) => {
        e.preventDefault()
        onContinue()
      }}
    >
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-xl font-bold">{t("auth.register.account.title")}</h1>
        <AboutLessleyDialog />
      </div>
      <FormField
        control={form.control}
        name="userName"
        render={({ field }) => (
          <FormItem className="space-y-1.5">
            <FormLabel>{t("auth.register.account.username")}</FormLabel>
            <FormControl>
              <Input {...field} autoComplete="username" className="h-12 rounded-2xl" />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={form.control}
        name="email"
        render={({ field }) => (
          <FormItem className="space-y-1.5">
            <FormLabel>{t("auth.register.account.email")}</FormLabel>
            <FormControl>
              <Input {...field} type="email" autoComplete="email" className="h-12 rounded-2xl" />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={form.control}
        name="password"
        render={({ field }) => (
          <FormItem className="space-y-1.5">
            <FormLabel>{t("auth.register.account.password")}</FormLabel>
            <FormControl>
              <PasswordInput {...field} autoComplete="new-password" className="h-12 rounded-2xl" />
            </FormControl>
            {/* State the character classes up front. They are the Gateway's own Identity
                rules, and a password that misses one otherwise only fails after Continue
                has already gone to the server. */}
            <FormDescription>{t("auth.passwordRequirements")}</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={form.control}
        name="verifyPassword"
        render={({ field }) => (
          <FormItem className="space-y-1.5">
            <FormLabel>{t("auth.register.account.verifyPassword")}</FormLabel>
            <FormControl>
              <PasswordInput {...field} autoComplete="new-password" className="h-12 rounded-2xl" />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <ErrorAlert message={serverError} />
      <Button type="submit" variant="hero" size="xl" disabled={isLoading}>
        {isLoading ? <Loader2 className="size-4 animate-spin" /> : null}
        {isLoading ? t("auth.register.verifyEmail.sendingCode") : t("common.continue")}
      </Button>
      <p className="text-center text-xs text-muted-foreground">
        {t("auth.register.account.alreadyHaveAccount")}{" "}
        <Link to={ROUTES.LOGIN} className="font-medium text-primary">
          {t("auth.register.account.signIn")}
        </Link>
      </p>
    </form>
  )
}
