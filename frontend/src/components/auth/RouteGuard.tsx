"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Loader2 } from "lucide-react"

interface RouteGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  redirectTo?: string
}

export function RouteGuard({
  children,
  requireAuth = true,
  redirectTo
}: RouteGuardProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading) {
      if (requireAuth && !isAuthenticated) {
        // Redirect to login if authentication is required but user is not authenticated
        const loginUrl = redirectTo || '/login'
        router.push(loginUrl)
      } else if (!requireAuth && isAuthenticated) {
        // Redirect away from auth pages if user is already authenticated
        router.push(redirectTo || '/')
      }
    }
  }, [isAuthenticated, isLoading, requireAuth, redirectTo, router])

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  // If authentication check is complete and conditions are met, render children
  if ((requireAuth && isAuthenticated) || (!requireAuth && !isAuthenticated)) {
    return <>{children}</>
  }

  // Return null while redirecting
  return null
}