import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useNavigate } from "react-router-dom"
import { CheckCircle2, CreditCard } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ErrorAlert } from "@/components/shared/ErrorAlert"
import { LoadingCard } from "@/components/shared/LoadingCard"
import { PageHeader } from "@/components/shared/PageHeader"
import { CLUBS, MATCH_LEVELS, formatCategoryLabel } from "@/lib/constants"
import { fintech } from "@/lib/fintech-styles"
import { cn, toggleArrayValue } from "@/lib/utils"
import { useInitOpenFinance, useMyProfile, useUpdateMyProfile } from "@/features/user/hooks"

const settingsSchema = z.object({
  clubs: z.array(z.string()),
  matchLevel: z.enum(["Low", "Medium", "High"]).nullable(),
  mutedTags: z.array(z.string()),
})

type SettingsValues = z.infer<typeof settingsSchema>

export function SettingsPage() {
  const navigate = useNavigate()
  const { data: profile, isLoading, error } = useMyProfile()
  const updateProfile = useUpdateMyProfile()
  const initOpenFinance = useInitOpenFinance()

  const form = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: { clubs: [], matchLevel: null, mutedTags: [] },
  })

  useEffect(() => {
    if (profile) {
      form.reset({
        clubs: profile.clubs ?? [],
        matchLevel: profile.matchLevel ?? null,
        mutedTags: profile.mutedTags ?? [],
      })
    }
  }, [profile, form])

  function onSubmit(values: SettingsValues) {
    updateProfile.mutate(values)
  }

  function handleConnectCard() {
    initOpenFinance.mutate(undefined, {
      onSuccess: (data) => {
        window.location.assign(data.connectUrl)
      },
    })
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader title="Settings" onBack={() => navigate(-1)} />

      <section className={fintech.page}>
        {isLoading ? (
          <LoadingCard message="Loading your settings…" />
        ) : error ? (
          <ErrorAlert message="Failed to load your profile. Please try again." />
        ) : profile ? (
          <>
            <Card className="fintech-card border-0">
              <CardContent className="space-y-3 px-5 py-4">
                <p className={fintech.sectionEyebrow}>Account</p>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Username</span>
                  <span className="text-sm font-medium text-slate-800">{profile.userName}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Email</span>
                  <span className="text-sm font-medium text-slate-800">{profile.email}</span>
                </div>
              </CardContent>
            </Card>

            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <Card className="fintech-card border-0">
                  <CardContent className="space-y-4 px-5 py-4">
                    <p className={fintech.sectionEyebrow}>Preferences</p>

                    <FormField
                      control={form.control}
                      name="clubs"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-sm">Loyalty clubs</FormLabel>
                          <div className="grid grid-cols-2 gap-1.5">
                            {CLUBS.map((club) => (
                              <label
                                key={club.id}
                                className={cn(
                                  "flex cursor-pointer select-none items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors",
                                  field.value.includes(club.id)
                                    ? "bg-violet-50 text-violet-800"
                                    : "text-slate-600 hover:bg-slate-100",
                                )}
                              >
                                <input
                                  type="checkbox"
                                  className="size-3.5 rounded accent-violet-600"
                                  checked={field.value.includes(club.id)}
                                  onChange={() =>
                                    field.onChange(toggleArrayValue(field.value, club.id))
                                  }
                                />
                                {club.name}
                              </label>
                            ))}
                          </div>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="matchLevel"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-sm">Match level</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value ?? ""}>
                            <FormControl>
                              <SelectTrigger className="fintech-input">
                                <SelectValue placeholder="Select match level" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {MATCH_LEVELS.map((level) => (
                                <SelectItem key={level} value={level}>
                                  {level === "High"
                                    ? "High (top 25%)"
                                    : level === "Medium"
                                      ? "Medium (top 50%)"
                                      : "Low (top 75%)"}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="mutedTags"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-sm">
                            Muted tags
                            {field.value.length > 0 ? (
                              <span className="ml-1.5 font-normal text-slate-400">
                                ({field.value.length} of {profile.tags.length} muted)
                              </span>
                            ) : null}
                          </FormLabel>
                          {profile.tags.length === 0 ? (
                            <p className="rounded-xl border border-slate-200/80 bg-white px-3 py-3 text-sm text-slate-400">
                              No tags yet — connect your bank to see available tags.
                            </p>
                          ) : (
                            <div className="max-h-40 space-y-0.5 overflow-y-auto rounded-xl border border-slate-200/80 bg-white p-2">
                              {profile.tags.map((tag) => (
                                <label
                                  key={tag}
                                  className={cn(
                                    "flex cursor-pointer select-none items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                                    field.value.includes(tag)
                                      ? "bg-red-50 text-red-700"
                                      : "text-slate-600 hover:bg-slate-50",
                                  )}
                                >
                                  <input
                                    type="checkbox"
                                    className="size-3.5 rounded accent-red-500"
                                    checked={field.value.includes(tag)}
                                    onChange={() =>
                                      field.onChange(toggleArrayValue(field.value, tag))
                                    }
                                  />
                                  {formatCategoryLabel(tag)}
                                </label>
                              ))}
                            </div>
                          )}
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </CardContent>
                </Card>

                {updateProfile.error ? (
                  <ErrorAlert
                    message={
                      updateProfile.error instanceof Error
                        ? updateProfile.error.message
                        : "Failed to save settings."
                    }
                  />
                ) : null}

                {updateProfile.isSuccess ? (
                  <div className="flex items-center gap-1.5 text-sm text-emerald-600">
                    <CheckCircle2 className="size-4" />
                    Settings saved
                  </div>
                ) : null}

                <Button
                  type="submit"
                  className="w-full"
                  disabled={updateProfile.isPending || !form.formState.isDirty}
                >
                  {updateProfile.isPending ? "Saving…" : "Save settings"}
                </Button>
              </form>
            </Form>

            <Card className="fintech-card border-0">
              <CardContent className="space-y-3 px-5 py-4">
                <p className={fintech.sectionEyebrow}>Open Banking</p>
                <p className="text-sm text-slate-500">
                  Connect an additional bank card to expand your transaction insights.
                </p>
                {initOpenFinance.error ? (
                  <p className="text-xs text-amber-700">
                    {initOpenFinance.error instanceof Error
                      ? initOpenFinance.error.message
                      : "Unable to start connection. Please try again."}
                  </p>
                ) : null}
                <Button
                  type="button"
                  variant="outline"
                  className="w-full gap-2"
                  onClick={handleConnectCard}
                  disabled={initOpenFinance.isPending}
                >
                  <CreditCard className="size-4" />
                  {initOpenFinance.isPending ? "Connecting…" : "Connect another card"}
                </Button>
              </CardContent>
            </Card>
          </>
        ) : null}
      </section>
    </div>
  )
}
