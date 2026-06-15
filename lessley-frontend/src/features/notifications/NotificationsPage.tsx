import { useEffect, useState } from "react"

import { ArrowLeft, Bell } from "lucide-react"



import { Button } from "@/components/ui/button"

import { Card, CardContent } from "@/components/ui/card"

import {

  NOTIFICATION_CATEGORY_LABELS,

  type AppNotificationWithRead,

  type NotificationCategory,

} from "@/features/notifications/notificationTypes"

import { getNotifications, markAllNotificationsRead } from "@/features/notifications/notificationsStore"

import { fintech } from "@/lib/fintech-styles"

import { cn } from "@/lib/utils"



interface NotificationsPageProps {

  onBack: () => void

  onReadStateChange: () => void

}



function categoryAccent(category: NotificationCategory) {

  switch (category) {

    case "missed_savings":

      return "border-amber-200/80 bg-amber-50 text-amber-800"

    case "hot_deal":

      return "border-rose-200/80 bg-rose-50 text-rose-800"

    case "monthly_report":

      return "border-indigo-200/80 bg-indigo-50 text-indigo-800"

    case "club_match":

      return "border-violet-200/80 bg-violet-50 text-violet-800"

    case "spending_insight":

      return "border-sky-200/80 bg-sky-50 text-sky-800"

    case "bank_sync":

      return "border-emerald-200/80 bg-emerald-50 text-emerald-800"

    case "welcome":

      return "border-slate-200/80 bg-slate-50 text-slate-700"

    default:

      return "border-slate-200/80 bg-slate-50 text-slate-700"

  }

}



function NotificationRow({ item }: { item: AppNotificationWithRead }) {

  return (

    <div

      className={cn(

        "fintech-card rounded-2xl p-4 transition-shadow",

        item.read ? "border-slate-200/60" : "border-violet-200/80 bg-violet-50/50 ring-1 ring-violet-100"

      )}

    >

      <div className="flex items-start gap-3">

        {!item.read ? (

          <span className="mt-2 size-2 shrink-0 rounded-full bg-violet-500" aria-hidden />

        ) : (

          <span className="mt-2 size-2 shrink-0" aria-hidden />

        )}

        <div className="min-w-0 flex-1 space-y-2">

          <div className="flex flex-wrap items-center gap-2">

            <span

              className={cn(

                "inline-flex rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",

                categoryAccent(item.category)

              )}

            >

              {NOTIFICATION_CATEGORY_LABELS[item.category]}

            </span>

            <span className="text-xs text-slate-400 tabular-nums">{item.time}</span>

          </div>

          <p className={cn("text-sm leading-relaxed", item.read ? "text-slate-600" : "font-medium text-slate-800")}>

            {item.message}

          </p>

          {item.deal_id ? (

            <p className="truncate text-xs text-slate-400">Deal · {item.deal_id}</p>

          ) : null}

        </div>

      </div>

    </div>

  )

}



export function NotificationsPage({ onBack, onReadStateChange }: NotificationsPageProps) {
  const [notifications] = useState(() => getNotifications())

  useEffect(() => {
    return () => {
      markAllNotificationsRead()
      onReadStateChange()
    }
  }, [onReadStateChange])



  const unread = notifications.filter((n) => !n.read)

  const read = notifications.filter((n) => n.read)



  return (

    <div className="flex min-h-full flex-col">

      <header className={fintech.subheader}>

        <Button

          type="button"

          variant="ghost"

          className="min-h-10 min-w-10 rounded-xl border border-slate-200/80 bg-white px-0 shadow-sm"

          onClick={onBack}

          aria-label="Back"

        >

          <ArrowLeft className="size-4" />

        </Button>

        <div className="min-w-0 flex-1">

          <h2 className="text-lg font-bold tracking-tight text-slate-900">Notifications</h2>

          <p className="text-xs text-slate-500">

            {unread.length ? `${unread.length} unread` : "You're all caught up"}

          </p>

        </div>

      </header>



      <div className="flex-1 space-y-6 px-4 py-4">

        {notifications.length === 0 ? (

          <Card className="fintech-card border-0">

            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">

              <div className="flex size-14 items-center justify-center rounded-2xl bg-slate-100">

                <Bell className="size-7 text-slate-300" />

              </div>

              <p className="text-sm text-slate-500">No notifications yet.</p>

            </CardContent>

          </Card>

        ) : null}



        {unread.length > 0 ? (

          <section className="space-y-2">

            <h3 className={fintech.sectionEyebrow}>Unread</h3>

            <div className="space-y-2">

              {unread.map((item) => (

                <NotificationRow key={item.id} item={item} />

              ))}

            </div>

          </section>

        ) : null}



        {read.length > 0 ? (

          <section className="space-y-2">

            <h3 className={fintech.sectionEyebrow}>Earlier</h3>

            <div className="space-y-2">

              {read.map((item) => (

                <NotificationRow key={item.id} item={item} />

              ))}

            </div>

          </section>

        ) : null}

      </div>

    </div>

  )

}

