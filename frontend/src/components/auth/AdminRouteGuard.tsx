"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Loader2 } from "lucide-react"

interface AdminRouteGuardProps {
  children: React.ReactNode
  requireSuperuser?: boolean
  redirectTo?: string
}

export function AdminRouteGuard({
  children,
  requireSuperuser = true,
  redirectTo
}: AdminRouteGuardProps) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        // Redirect to login if not authenticated
        const loginUrl = redirectTo || '/login'
        router.push(loginUrl)
      } else if (requireSuperuser && !user?.is_superuser) {
        // Redirect to home if not superuser
        router.push(redirectTo || '/')
      }
    }
  }, [isAuthenticated, isLoading, user, requireSuperuser, redirectTo, router])

  // Show loading spinner while checking authentication and role
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  // If authentication and role checks pass, render children
  if (isAuthenticated && (!requireSuperuser || user?.is_superuser)) {
    return <>{children}</>
  }

  // Return null while redirecting
  return null
}