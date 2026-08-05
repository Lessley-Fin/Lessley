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
import { loginWithGateway } from "../api"
import { loginSchema, type LoginValues } from "../schemas"
import { usePostAuth } from "../usePostAuth"

export function LoginForm() {
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
        message: error instanceof Error ? error.message : "Sign-in failed. Please try again.",
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
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <PasswordInput {...field} autoComplete="current-password" disabled={isLoading} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <ErrorAlert message={serverError} />
        <Button type="submit" className="min-h-12 w-full" disabled={isLoading}>
          {isLoading ? <Loader2 className="size-4 animate-spin" /> : null}
          {isLoading ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </Form>
  )
}
