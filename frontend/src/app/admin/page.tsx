"use client"

import { useState, useEffect } from "react"
import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { AdminRouteGuard } from "@/components/auth/AdminRouteGuard"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { toast } from "sonner"
import { adminAPI } from "@/lib/api/admin"
import { analyticsAPI } from "@/lib/api/analytics"
import { SystemStats, UserStats, SearchStats, CircuitBreakerStats } from "@/types/api"
import { Loader2, Users, Database, Search, Activity, Trash2, RotateCcw, Shield, AlertTriangle } from "lucide-react"
import { SystemStatsCard } from "@/components/admin/SystemStatsCard"
import { CacheManagementCard } from "@/components/admin/CacheManagementCard"
import { IndexManagementCard } from "@/components/admin/IndexManagementCard"
import { UserManagementCard } from "@/components/admin/UserManagementCard"
import { AuditTrailCard } from "@/components/admin/AuditTrailCard"

function AdminDashboard() {
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [searchStats, setSearchStats] = useState<SearchStats | null>(null)
  const [circuitBreakers, setCircuitBreakers] = useState<Record<string, CircuitBreakerStats> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStats = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const [sysStats, usrStats, srchStats, circuitStats] = await Promise.allSettled([
        adminAPI.getSystemStats(),
        adminAPI.getUserStats(),
        adminAPI.getSearchStats(),
        analyticsAPI.getCircuitBreakerStats()
      ])

      if (sysStats.status === 'fulfilled') setSystemStats(sysStats.value)
      if (usrStats.status === 'fulfilled') setUserStats(usrStats.value)
      if (srchStats.status === 'fulfilled') setSearchStats(srchStats.value)
      if (circuitStats.status === 'fulfilled') setCircuitBreakers(circuitStats.value)
    } catch (err: any) {
      setError(err.detail || "Failed to load admin statistics")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  if (isLoading) {
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
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <Button onClick={loadStats} variant="outline" size="sm">
            <RotateCcw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <SystemStatsCard stats={systemStats} />
          <UserManagementCard stats={userStats} />
          <IndexManagementCard stats={searchStats} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CacheManagementCard />
          <AuditTrailCard />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Security Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              {circuitBreakers ? (
                <div className="space-y-4">
                  <div className="grid gap-2">
                    {Object.entries(circuitBreakers).map(([service, stats]) => (
                      <div key={service} className="flex items-center justify-between p-2 border rounded">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            stats.state === 'closed' ? 'bg-green-500' :
                            stats.state === 'open' ? 'bg-red-500' : 'bg-yellow-500'
                          }`} />
                          <span className="text-sm font-medium capitalize">{service}</span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {stats.failures} failures
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="pt-2 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        try {
                          await analyticsAPI.resetCircuitBreakers()
                          toast.success("Circuit breakers reset successfully")
                          loadStats()
                        } catch (error: any) {
                          toast.error("Failed to reset circuit breakers: " + error.detail)
                        }
                      }}
                    >
                      Reset All Circuit Breakers
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Security monitoring data will be displayed here.
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Security Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center gap-2 p-2 bg-green-50 border border-green-200 rounded">
                  <Shield className="h-4 w-4 text-green-600" />
                  <span className="text-sm">All systems operational</span>
                </div>
                <div className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded">
                  <Activity className="h-4 w-4 text-blue-600" />
                  <span className="text-sm">Rate limiting active</span>
                </div>
                <div className="flex items-center gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <span className="text-sm">Monitor failed login attempts</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </SidebarNav>
  )
}

export default function AdminPage() {
  return (
    <AdminRouteGuard requireSuperuser={true}>
      <AdminDashboard />
    </AdminRouteGuard>
  )
}