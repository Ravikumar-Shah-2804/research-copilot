'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Shield, AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
  isSecurityError: boolean
}

export class SecurityErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, isSecurityError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    // Check if this is a security-related error
    const isSecurityError = error.message.includes('security') ||
                           error.message.includes('authentication') ||
                           error.message.includes('authorization') ||
                           error.message.includes('forbidden') ||
                           error.message.includes('rate limit') ||
                           error.message.includes('403') ||
                           error.message.includes('401')

    return {
      hasError: true,
      error,
      isSecurityError
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Security Error Boundary caught an error:', error, errorInfo)

    // Log security events
    if (this.state.isSecurityError) {
      // TODO: Send to security monitoring service
      console.warn('Security-related error detected:', error.message)
    }

    this.props.onError?.(error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, isSecurityError: false })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                {this.state.isSecurityError ? (
                  <Shield className="h-5 w-5" />
                ) : (
                  <AlertTriangle className="h-5 w-5" />
                )}
                {this.state.isSecurityError ? 'Security Error' : 'Application Error'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert variant={this.state.isSecurityError ? "destructive" : "default"}>
                <AlertDescription>
                  {this.state.isSecurityError
                    ? 'A security-related error occurred. This incident has been logged for review.'
                    : 'An unexpected error occurred in the application.'
                  }
                </AlertDescription>
              </Alert>

              <div className="text-sm text-muted-foreground">
                <p className="font-medium">Error Details:</p>
                <p className="mt-1 break-words">{this.state.error?.message}</p>
              </div>

              <div className="flex gap-2">
                <Button onClick={this.handleRetry} className="flex-1">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </Button>
                <Button
                  variant="outline"
                  onClick={() => window.location.reload()}
                  className="flex-1"
                >
                  Reload Page
                </Button>
              </div>

              {this.state.isSecurityError && (
                <div className="pt-2 border-t">
                  <p className="text-xs text-muted-foreground">
                    If this error persists, please contact your system administrator.
                    Reference ID: {Date.now()}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

// Hook for functional components
export const useSecurityErrorHandler = () => {
  return (error: Error, errorInfo?: ErrorInfo) => {
    console.error('Security error handler:', error, errorInfo)

    // Check if security error
    const isSecurityError = error.message.includes('security') ||
                           error.message.includes('authentication') ||
                           error.message.includes('authorization')

    if (isSecurityError) {
      // TODO: Report to security monitoring
      console.warn('Security error reported:', error.message)
    }
  }
}