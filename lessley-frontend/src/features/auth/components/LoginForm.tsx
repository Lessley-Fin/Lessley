import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2, Sparkles } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { ROUTES } from "@/lib/routes"
import { loginWithGateway } from "../api"
import { loginSchema, type LoginValues } from "../schemas"
import { usePostAuth } from "../usePostAuth"

export function LoginForm() {
  const { t } = useTranslation()
  const postAuth = usePostAuth()

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { userName: "", password: "" },
  })

  const isLoading = form.formState.isSubmitting
  const serverError = form.formState.errors.root?.message

  const handleSubmit = form.handleSubmit(async (values) => {
    try {
      const data = await loginWithGateway({ userName: values.userName, password: values.password })
      await postAuth({ userName: data.userName ?? values.userName, email: data.email })
    } catch (error) {
      form.setError("root", {
        message: error instanceof Error ? error.message : t("auth.login.signInFailed"),
      })
    }
  })

  return (
    <Form {...form}>
      <form className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]" onSubmit={handleSubmit}>
        <FormField
          control={form.control}
          name="userName"
          render={({ field }) => (
            <FormItem className="space-y-1.5">
              <FormLabel>{t("auth.login.username")}</FormLabel>
              <FormControl>
                <Input {...field} autoComplete="username" className="h-12 rounded-2xl" disabled={isLoading} />
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
              <FormLabel>{t("auth.login.password")}</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  type="password"
                  autoComplete="current-password"
                  className="h-12 rounded-2xl"
                  disabled={isLoading}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <Link to={ROUTES.FORGOT_PASSWORD} className="text-xs font-medium text-primary hover:underline">
            {t("auth.login.forgotPassword")}
          </Link>
        </div>
        <ErrorAlert message={serverError} />
        <Button type="submit" variant="hero" size="xl" disabled={isLoading}>
          {isLoading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles />}
          {isLoading ? t("auth.login.signingIn") : t("auth.login.signIn")}
        </Button>
        <Button asChild variant="pill" size="xl">
          <Link to={ROUTES.REGISTER}>{t("auth.login.createAccount")}</Link>
        </Button>
      </form>
    </Form>
  )
}
