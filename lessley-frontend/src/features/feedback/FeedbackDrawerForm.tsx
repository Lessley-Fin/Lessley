import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { submitFeedback } from "@/lib/api"
import type { FeedbackItem, FeedbackSubmission } from "@/lib/types"

const feedbackSchema = z.object({
  description: z.string().min(5, "Describe your feedback in at least 5 characters."),
  category: z.enum(["Bug", "UI", "General"]),
})

type FeedbackFormValues = z.infer<typeof feedbackSchema>

interface FeedbackDrawerFormProps {
  onSubmitted: (item: FeedbackItem) => void
}

export function FeedbackDrawerForm({ onSubmitted }: FeedbackDrawerFormProps) {
  const form = useForm<FeedbackFormValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      description: "",
      category: "General",
    },
  })

  const onSubmit = async (values: FeedbackFormValues) => {
    const payload: FeedbackSubmission = {
      description: values.description,
      category: values.category,
    }

    await submitFeedback(payload)

    onSubmitted({
      id: crypto.randomUUID(),
      summary: values.description,
      category: values.category,
      createdAt: "Just now",
    })

    form.reset({
      description: "",
      category: "General",
    })
  }

  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button
          className="fixed bottom-6 right-6 z-40 min-h-12 min-w-12 rounded-full bg-slate-900 px-4 text-white shadow-[0_10px_25px_rgba(15,23,42,0.28)]"
          size="icon"
          aria-label="Open feedback form"
        >
          +
        </Button>
      </DrawerTrigger>
      <DrawerContent className="mx-auto w-full max-w-md rounded-t-3xl border-0 bg-white pb-2">
        <DrawerHeader className="px-6 pt-6">
          <DrawerTitle>New feedback</DrawerTitle>
          <DrawerDescription>Share what should be improved in Lessley.</DrawerDescription>
        </DrawerHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5 px-6 pb-3">
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Tell us what happened..."
                      className="min-h-28 border-0 bg-slate-100 px-4 py-3 shadow-none focus-visible:ring-slate-300"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Category</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="min-h-12 border-0 bg-slate-100 px-4 shadow-none focus:ring-slate-300">
                        <SelectValue placeholder="Choose a category" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="Bug">Bug</SelectItem>
                      <SelectItem value="UI">UI</SelectItem>
                      <SelectItem value="General">General</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DrawerFooter className="px-0">
              <Button className="min-h-12 rounded-xl" type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? <Loader2 className="size-4 animate-spin" /> : null}
                Submit feedback
              </Button>
              <DrawerClose asChild>
                <Button className="min-h-12 rounded-xl border-0 bg-slate-100 text-slate-700" type="button" variant="outline">
                  Cancel
                </Button>
              </DrawerClose>
            </DrawerFooter>
          </form>
        </Form>
      </DrawerContent>
    </Drawer>
  )
}
