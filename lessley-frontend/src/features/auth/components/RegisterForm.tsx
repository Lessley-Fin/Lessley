import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"

import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { PasswordInput } from "@/components/shared/PasswordInput"
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
import { loginWithGateway, registerWithGateway } from "../api"
import { registerSchema, type RegisterValues } from "../schemas"
import { usePostAuth } from "../usePostAuth"
import { PersonalizationSection } from "./PersonalizationSection"

export function RegisterForm() {
  const postAuth = usePostAuth()

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { userName: "", email: "", password: "", clubs: [], matchLevel: undefined, mutedCategories: [] },
  })

  const isLoading = form.formState.isSubmitting
  const serverError = form.formState.errors.root?.message

  const handleSubmit = form.handleSubmit(async (values) => {
    try {
      await registerWithGateway({
        userName: values.userName,
        email: values.email,
        password: values.password,
        clubs: values.clubs?.length ? values.clubs : undefined,
        matchLevel: values.matchLevel,
        mutedCategories: values.mutedCategories?.length ? values.mutedCategories : undefined,
      })
      const data = await loginWithGateway({ userName: values.userName, password: values.password })
      await postAuth({ userName: data.userName ?? values.userName, email: data.email ?? values.email })
    } catch (error) {
      form.setError("root", {
        message: error instanceof Error ? error.message : "Registration failed. Please try again.",
      })
    }
  })

  return (
    <Form {...form}>
      <form className="space-y-5" onSubmit={handleSubmit}>
        <FormField
          control={form.control}
          name="userName"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input {...field} autoComplete="username" className="fintech-input" disabled={isLoading} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input {...field} type="email" autoComplete="email" className="fintech-input" disabled={isLoading} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <PasswordInput {...field} autoComplete="new-password" disabled={isLoading} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <PersonalizationSection form={form} isLoading={isLoading} />

        <ErrorAlert message={serverError} />
        <Button type="submit" className="min-h-12 w-full" disabled={isLoading}>
          {isLoading ? <Loader2 className="size-4 animate-spin" /> : null}
          {isLoading ? "Creating account..." : "Create account"}
        </Button>
      </form>
    </Form>
  )
}
