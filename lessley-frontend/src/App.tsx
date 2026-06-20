import { useEffect } from "react"
import { RouterProvider } from "react-router-dom"
import { QueryClientProvider } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"

import { ErrorBoundary } from "@/components/ErrorBoundary"
import { useAuthStore } from "@/features/auth/store"
import { queryClient } from "@/lib/query-client"
import { router } from "@/routes"

function App() {
  useEffect(() => {
    useAuthStore.getState().initialize()
  }, [])

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
