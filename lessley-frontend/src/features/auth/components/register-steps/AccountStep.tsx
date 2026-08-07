import type { UseFormReturn } from "react-hook-form"
import { Link } from "react-router-dom"

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
  return (
    <form
      className="space-y-4 rounded-3xl bg-card p-6 shadow-[var(--shadow-card)]"
      onSubmit={(e) => {
        e.preventDefault()
        onContinue()
      }}
    >
      <h1 className="text-xl font-bold">Create account</h1>
      <FormField
        control={form.control}
        name="userName"
        render={({ field }) => (
          <FormItem className="space-y-1.5">
            <FormLabel>Username</FormLabel>
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
            <FormLabel>Email</FormLabel>
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
            <FormLabel>Password</FormLabel>
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
            <FormLabel>Verify password</FormLabel>
            <FormControl>
              <Input {...field} type="password" autoComplete="new-password" className="h-12 rounded-2xl" />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <Button type="submit" variant="hero" size="xl">
        Continue
      </Button>
      <p className="text-center text-xs text-muted-foreground">
        Already have an account?{" "}
        <Link to={ROUTES.LOGIN} className="font-medium text-primary">
          Sign in
        </Link>
      </p>
    </form>
  )
}
