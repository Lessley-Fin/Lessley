import type { UseFormReturn } from "react-hook-form"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { ROUTES } from "@/lib/routes"
import type { RegisterValues } from "../../schemas"

interface AccountStepProps {
  form: UseFormReturn<RegisterValues>
  onContinue: () => void
}

export function AccountStep({ form, onContinue }: AccountStepProps) {
  const { t } = useTranslation()
  return (
    <form
      className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]"
      onSubmit={(e) => {
        e.preventDefault()
        onContinue()
      }}
    >
      <h1 className="text-xl font-bold">{t("auth.register.account.title")}</h1>
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
              <Input {...field} type="password" autoComplete="new-password" className="h-12 rounded-2xl" />
            </FormControl>
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
              <Input {...field} type="password" autoComplete="new-password" className="h-12 rounded-2xl" />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <Button type="submit" variant="hero" size="xl">
        {t("common.continue")}
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
