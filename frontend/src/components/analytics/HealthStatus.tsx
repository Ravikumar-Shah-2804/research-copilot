"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AlertTriangle, CheckCircle, XCircle, RefreshCw } from "lucide-react"
import { CircuitBreakerStats } from "@/types/api"
import { analyticsAPI } from "@/lib/api/analytics"
import { useState } from "react"

interface HealthStatusProps {
  health: any
  circuitBreakers: Record<string, CircuitBreakerStats> | null
}

export function HealthStatus({ health, circuitBreakers }: HealthStatusProps) {
  const [resetting, setResetting] = useState<string | null>(null)

  const getHealthIcon = (status: boolean) => {
    return status ? (
      <CheckCircle className="h-4 w-4 text-green-600" />
    ) : (
      <XCircle className="h-4 w-4 text-red-600" />
    )
  }

  const getCircuitBreakerIcon = (state: string) => {
    switch (state.toLowerCase()) {
      case 'closed':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'open':
        return <XCircle className="h-4 w-4 text-red-600" />
      case 'half_open':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />
      default:
        return <RefreshCw className="h-4 w-4 text-gray-600" />
    }
  }

  const handleResetCircuitBreaker = async (service: string) => {
    try {
      setResetting(service)
      await analyticsAPI.resetCircuitBreakers()
      // In a real app, you'd refresh the data here
      window.location.reload()
    } catch (error) {
      console.error('Failed to reset circuit breakers:', error)
    } finally {
      setResetting(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* System Services Health */}
      <Card>
        <CardHeader>
          <CardTitle>System Services</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {health?.services && Object.entries(health.services).map(([service, status]: [string, any]) => (
              <div key={service} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-2">
                  {getHealthIcon(status.healthy)}
                  <div>
                    <p className="font-medium capitalize">{service.replace('_', ' ')}</p>
                    <p className="text-sm text-muted-foreground">
                      {status.response_time ? `${status.response_time}ms` : 'N/A'}
                    </p>
                  </div>
                </div>
                <Badge variant={status.healthy ? "default" : "destructive"}>
                  {status.healthy ? 'Healthy' : 'Unhealthy'}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Circuit Breakers */}
      {circuitBreakers && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Circuit Breakers</CardTitle>
            <Button
              onClick={() => handleResetCircuitBreaker('all')}
              disabled={resetting === 'all'}
              size="sm"
            >
              {resetting === 'all' ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                'Reset All'
              )}
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(circuitBreakers).map(([service, stats]) => (
                <div key={service} className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getCircuitBreakerIcon(stats.state)}
                      <p className="font-medium capitalize">{service.replace('_', ' ')}</p>
                    </div>
                    <Badge variant={
                      stats.state === 'closed' ? 'default' :
                      stats.state === 'open' ? 'destructive' : 'secondary'
                    }>
                      {stats.state.replace('_', ' ')}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>Failures: {stats.failures}</p>
                    {stats.last_failure_time && (
                      <p>Last failure: {new Date(stats.last_failure_time).toLocaleString()}</p>
                    )}
                    {stats.next_retry_time && (
                      <p>Next retry: {new Date(stats.next_retry_time).toLocaleString()}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Overall System Status */}
      <Card>
        <CardHeader>
          <CardTitle>Overall Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            {getHealthIcon(health?.status === 'healthy')}
            <div>
              <p className="text-lg font-medium">
                System is {health?.status === 'healthy' ? 'Healthy' : 'Unhealthy'}
              </p>
              <p className="text-sm text-muted-foreground">
                Last checked: {health?.timestamp ? new Date(health.timestamp).toLocaleString() : 'Unknown'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}