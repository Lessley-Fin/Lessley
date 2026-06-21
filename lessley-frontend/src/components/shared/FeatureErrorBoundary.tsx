import { Component, type ErrorInfo, type ReactNode } from "react"
import { AlertTriangle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

interface Props {
  children: ReactNode
  featureName?: string
}

interface State {
  hasError: boolean
}

export class FeatureErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`FeatureErrorBoundary [${this.props.featureName ?? "unknown"}]:`, error, info.componentStack)
  }

  handleReset = () => {
    this.setState({ hasError: false })
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <Card className="fintech-card border-0" role="alert">
        <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-red-50 text-red-500">
            <AlertTriangle className="size-7" />
          </div>
          <div>
            <p className="font-semibold text-slate-800">Something went wrong</p>
            <p className="mt-1 text-sm text-slate-500">
              {this.props.featureName
                ? `The ${this.props.featureName} section encountered an error.`
                : "An unexpected error occurred."}
            </p>
          </div>
          <Button onClick={this.handleReset} className="min-h-10">
            Try again
          </Button>
        </CardContent>
      </Card>
    )
  }
}
