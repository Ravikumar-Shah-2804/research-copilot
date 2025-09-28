"use client"

import { useState, useEffect } from "react"
import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { RouteGuard } from "@/components/auth/RouteGuard"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useAuth } from "@/lib/auth-context"
import { analyticsAPI } from "@/lib/api/analytics"
import { Loader2, Activity, TrendingUp, DollarSign, Users, AlertTriangle, CheckCircle, XCircle } from "lucide-react"
import {
  PerformanceMetrics,
  SearchAnalytics,
  UsageMetrics,
  UsageTrends,
  BillingMetrics,
  CircuitBreakerStats
} from "@/types/api"
import { UsageChart } from "@/components/analytics/UsageChart"
import { PerformanceChart } from "@/components/analytics/PerformanceChart"
import { HealthStatus } from "@/components/analytics/HealthStatus"

function AnalyticsDashboard() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Analytics data states
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null)
  const [searchAnalytics, setSearchAnalytics] = useState<SearchAnalytics | null>(null)
  const [userUsage, setUserUsage] = useState<UsageMetrics | null>(null)
  const [usageTrends, setUsageTrends] = useState<UsageTrends | null>(null)
  const [billingInfo, setBillingInfo] = useState<BillingMetrics | null>(null)
  const [circuitBreakers, setCircuitBreakers] = useState<Record<string, CircuitBreakerStats> | null>(null)
  const [systemHealth, setSystemHealth] = useState<any>(null)

  useEffect(() => {
    if (user) {
      loadAnalyticsData()
    }
  }, [user])

  const loadAnalyticsData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Load user-specific analytics data
      const userUsagePromise = user ? analyticsAPI.getUserUsage(user.id, undefined, undefined) : Promise.reject("No user")
      const usageTrendsPromise = user?.is_superuser ? analyticsAPI.getUsageTrends() : analyticsAPI.getUsageTrends(undefined, undefined, user?.organization_id)
      const billingPromise = user?.organization_id ? analyticsAPI.getBillingInfo(user.organization_id) : Promise.reject("No org")
      const healthPromise = analyticsAPI.getSystemHealth()

      // Admin-only calls (may fail)
      const performancePromise = analyticsAPI.getPerformanceMetrics()
      const searchPromise = analyticsAPI.getSearchAnalytics()
      const breakersPromise = analyticsAPI.getCircuitBreakerStats()

      const [
        userUsageResult,
        usageTrendsResult,
        billingResult,
        healthResult,
        performanceResult,
        searchResult,
        breakersResult
      ] = await Promise.allSettled([
        userUsagePromise,
        usageTrendsPromise,
        billingPromise,
        healthPromise,
        performancePromise,
        searchPromise,
        breakersPromise
      ])

      // Handle results
      console.log('Analytics API results:', {
        userUsage: userUsageResult.status,
        usageTrends: usageTrendsResult.status,
        billing: billingResult.status,
        health: healthResult.status,
        performance: performanceResult.status,
        search: searchResult.status,
        breakers: breakersResult.status
      })

      if (userUsageResult.status === 'fulfilled') {
        console.log('User usage:', userUsageResult.value)
        setUserUsage(userUsageResult.value)
      } else {
        console.error('User usage failed:', userUsageResult.reason)
      }

      if (usageTrendsResult.status === 'fulfilled') setUsageTrends(usageTrendsResult.value)
      if (billingResult.status === 'fulfilled') setBillingInfo(billingResult.value)
      if (healthResult.status === 'fulfilled') setSystemHealth(healthResult.value)
      if (performanceResult.status === 'fulfilled') setPerformanceMetrics(performanceResult.value)
      if (searchResult.status === 'fulfilled') setSearchAnalytics(searchResult.value)
      if (breakersResult.status === 'fulfilled') setCircuitBreakers(breakersResult.value)

    } catch (err: any) {
      setError(err.detail || "Failed to load analytics data")
    } finally {
      setLoading(false)
    }
  }

  const getHealthStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'ok':
        return 'text-green-600'
      case 'warning':
      case 'degraded':
        return 'text-yellow-600'
      case 'error':
      case 'unhealthy':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getHealthIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'ok':
        return <CheckCircle className="h-4 w-4" />
      case 'warning':
      case 'degraded':
        return <AlertTriangle className="h-4 w-4" />
      case 'error':
      case 'unhealthy':
        return <XCircle className="h-4 w-4" />
      default:
        return <Activity className="h-4 w-4" />
    }
  }

  if (loading) {
    return (
      <SidebarNav>
        <div className="p-6">
          <div className="flex items-center justify-center min-h-[400px]">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        </div>
      </SidebarNav>
    )
  }

  return (
    <SidebarNav>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Analytics Dashboard</h1>
          <button
            onClick={loadAnalyticsData}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            disabled={loading}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Refresh"}
          </button>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="usage">Usage</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="billing">Billing</TabsTrigger>
            <TabsTrigger value="health">System Health</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            {/* Key Metrics Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {performanceMetrics?.total_requests?.toLocaleString() || 'N/A'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    System requests
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Search Queries</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {searchAnalytics?.total_queries?.toLocaleString() || 'N/A'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Total searches
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Your Usage</CardTitle>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {userUsage?.total_api_calls?.toLocaleString() || 'N/A'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Your requests
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Tokens Used</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {userUsage?.rag_usage?.total_tokens_used?.toLocaleString() || 'N/A'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    RAG tokens consumed
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    ${billingInfo?.billing?.total_cost?.toFixed(2) || 'N/A'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Billing period
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* System Health Overview */}
            <Card>
              <CardHeader>
                <CardTitle>System Health</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {systemHealth?.services && Object.entries(systemHealth.services).map(([service, status]: [string, any]) => (
                    <div key={service} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-2">
                        {getHealthIcon(status.healthy ? 'healthy' : 'unhealthy')}
                        <span className="font-medium capitalize">{service.replace('_', ' ')}</span>
                      </div>
                      <Badge variant={status.healthy ? "default" : "destructive"}>
                        {status.healthy ? 'Healthy' : 'Unhealthy'}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="usage" className="space-y-6">
            {usageTrends && <UsageChart data={usageTrends} />}
            {userUsage && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle>Your Usage Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <p className="text-sm font-medium">Total Requests</p>
                        <p className="text-2xl font-bold">{userUsage.total_api_calls.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium">Total Tokens</p>
                        <p className="text-2xl font-bold">{userUsage.rag_usage.total_tokens_used.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium">RAG Queries</p>
                        <p className="text-2xl font-bold">{userUsage.rag_usage.rag_queries_count.toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Period: {new Date(userUsage.period.start_date).toLocaleDateString()} - {new Date(userUsage.period.end_date).toLocaleDateString()}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>RAG Usage Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <p className="text-sm font-medium">Total Tokens Used</p>
                        <p className="text-2xl font-bold">{userUsage.rag_usage.total_tokens_used.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium">Average Confidence</p>
                        <p className="text-2xl font-bold">{(userUsage.rag_usage.average_confidence * 100).toFixed(1)}%</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium">Sources Retrieved</p>
                        <p className="text-2xl font-bold">{userUsage.rag_usage.total_sources_retrieved.toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Based on {userUsage.rag_usage.rag_queries_count} RAG queries
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </TabsContent>

          <TabsContent value="performance" className="space-y-6">
            {performanceMetrics && <PerformanceChart data={performanceMetrics} />}
            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-medium">Uptime</p>
                    <p className="text-2xl font-bold">{Math.floor((performanceMetrics?.uptime_seconds || 0) / 3600)}h</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium">Error Rate</p>
                    <p className="text-2xl font-bold">{((performanceMetrics?.error_rate || 0) * 100).toFixed(2)}%</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="billing" className="space-y-6">
            {billingInfo && (
              <Card>
                <CardHeader>
                  <CardTitle>Billing Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-sm font-medium">Total Cost</p>
                      <p className="text-2xl font-bold">${billingInfo.total_cost.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium">Usage Cost</p>
                      <p className="text-2xl font-bold">${billingInfo.billing.total_cost.toFixed(2)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="health" className="space-y-6">
            <HealthStatus health={systemHealth} circuitBreakers={circuitBreakers} />
          </TabsContent>
        </Tabs>
      </div>
    </SidebarNav>
  )
}

export default function AnalyticsPage() {
  return (
    <RouteGuard requireAuth={true}>
      <AnalyticsDashboard />
    </RouteGuard>
  )
}