"use client"

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { RouteGuard } from "@/components/auth/RouteGuard"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useAuth } from "@/lib/auth-context"
import { analyticsAPI } from "@/lib/api/analytics"
import { Loader2, Activity, DollarSign, TrendingUp } from "lucide-react"
import { UsageMetrics, BillingMetrics } from "@/types/api"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { profileSchema, ProfileFormData } from "@/lib/schemas/auth"
import { sanitizeString } from "@/lib/utils/sanitization"

function ProfileForm() {
  const { user, refreshUser } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [userUsage, setUserUsage] = useState<UsageMetrics | null>(null)
  const [billingInfo, setBillingInfo] = useState<BillingMetrics | null>(null)

  const form = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: "",
    },
  })

  useEffect(() => {
    if (user) {
      form.reset({
        full_name: user.full_name || "",
      })
    }
  }, [user, form])

  useEffect(() => {
    if (user) {
      loadAnalyticsData()
    }
  }, [user])

  const loadAnalyticsData = async () => {
    try {
      setAnalyticsLoading(true)
      const [usage, billing] = await Promise.allSettled([
        analyticsAPI.getUserUsage(user!.id),
        user!.organization_id ? analyticsAPI.getBillingInfo(user!.organization_id) : Promise.reject("No org")
      ])

      if (usage.status === 'fulfilled') setUserUsage(usage.value)
      if (billing.status === 'fulfilled') setBillingInfo(billing.value)
    } catch (error) {
      console.error('Failed to load analytics data:', error)
    } finally {
      setAnalyticsLoading(false)
    }
  }

  const onSubmit = async (data: ProfileFormData) => {
    setMessage("")
    setIsLoading(true)

    try {
      // Sanitize input
      const sanitizedData = {
        full_name: data.full_name ? sanitizeString(data.full_name) : undefined,
      }

      // TODO: Implement profile update API call when available
      // For now, just show a message
      console.log('Sanitized profile data:', sanitizedData)
      setMessage("Profile update functionality will be implemented when the backend API is ready.")
    } catch (error: any) {
      setMessage(error.detail || "Failed to update profile.")
    } finally {
      setIsLoading(false)
    }
  }

  if (!user) {
    return (
      <SidebarNav>
        <div className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        </div>
      </SidebarNav>
    )
  }

  return (
    <SidebarNav>
      <div className="p-6 space-y-6">
        <h1 className="text-xl font-semibold">Profile</h1>

        {message && (
          <Alert>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Your Information</CardTitle>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-3">
                <div className="grid gap-1.5">
                  <label className="text-sm" htmlFor="username">Username</label>
                  <Input
                    id="username"
                    placeholder="Your username"
                    value={user?.username || ""}
                    disabled
                  />
                  <p className="text-xs text-muted-foreground">Username cannot be changed</p>
                </div>
                <div className="grid gap-1.5">
                  <label className="text-sm" htmlFor="email">Email</label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={user?.email || ""}
                    disabled
                  />
                  <p className="text-xs text-muted-foreground">Email cannot be changed</p>
                </div>
                <FormField
                  control={form.control}
                  name="full_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Full Name</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Your full name"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="pt-2">
                  <Button type="submit" disabled={isLoading}>
                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Save changes
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Account Details</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <div className="grid gap-1.5">
              <label className="text-sm">Account Status</label>
              <p className={`text-sm ${user.is_active ? 'text-green-600' : 'text-red-600'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </p>
            </div>
            <div className="grid gap-1.5">
              <label className="text-sm">Role</label>
              <p className="text-sm">{user.is_superuser ? 'Administrator' : 'User'}</p>
            </div>
            <div className="grid gap-1.5">
              <label className="text-sm">Member Since</label>
              <p className="text-sm">{new Date(user.created_at).toLocaleDateString()}</p>
            </div>
          </CardContent>
        </Card>

        {/* Usage Analytics Section */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Usage Analytics
            </CardTitle>
          </CardHeader>
          <CardContent>
            {analyticsLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : userUsage ? (
              <div className="grid gap-4 md:grid-cols-3">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {userUsage.total_requests.toLocaleString()}
                  </div>
                  <p className="text-sm text-muted-foreground">Total Requests</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {userUsage.total_tokens.toLocaleString()}
                  </div>
                  <p className="text-sm text-muted-foreground">Tokens Used</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    ${userUsage.total_cost.toFixed(2)}
                  </div>
                  <p className="text-sm text-muted-foreground">Total Cost</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No usage data available</p>
            )}
          </CardContent>
        </Card>

        {/* Billing Information Section */}
        {billingInfo && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Billing Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm font-medium">Current Period Cost</p>
                  <p className="text-2xl font-bold">${billingInfo.total_cost.toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">
                    Usage: ${billingInfo.usage.total_cost.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Organization</p>
                  <p className="text-sm">{billingInfo.billing?.organization_name || 'N/A'}</p>
                  <p className="text-xs text-muted-foreground">
                    Plan: {billingInfo.billing?.subscription_tier || 'N/A'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </SidebarNav>
  )
}

export default function ProfilePage() {
  return (
    <RouteGuard requireAuth={true}>
      <ProfileForm />
    </RouteGuard>
  )
}