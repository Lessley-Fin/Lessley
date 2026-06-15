import { ArrowLeft, Settings, SlidersHorizontal } from "lucide-react"



import { Button } from "@/components/ui/button"

import { Card, CardContent } from "@/components/ui/card"

import { fintech } from "@/lib/fintech-styles"



interface SettingsPageProps {

  onBack: () => void

}



export function SettingsPage({ onBack }: SettingsPageProps) {

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

        <h2 className="text-lg font-bold tracking-tight text-slate-900">Settings</h2>

      </header>



      <div className="flex flex-1 items-center justify-center px-5 py-8">

        <Card className="fintech-card w-full border-0">

          <CardContent className="flex flex-col items-center gap-4 py-14 text-center">

            <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-50 to-violet-100 text-violet-600">

              <SlidersHorizontal className="size-7" />

            </div>

            <div>

              <p className="font-semibold text-slate-800">Preferences coming soon</p>

              <p className="mt-1 text-sm text-slate-500">

                Account controls and notification settings will live here.

              </p>

            </div>

            <Settings className="size-4 text-slate-300" aria-hidden />

          </CardContent>

        </Card>

      </div>

    </div>

  )

}

