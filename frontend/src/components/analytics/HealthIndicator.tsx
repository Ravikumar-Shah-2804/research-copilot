"use client"

import { useState, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { AlertTriangle, CheckCircle, XCircle, Activity } from "lucide-react"
import { analyticsAPI } from "@/lib/api/analytics"

export function HealthIndicator() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const healthData = await analyticsAPI.getSystemHealth()
        setHealth(healthData)
      } catch (error) {
        console.error('Failed to load health status:', error)
      } finally {
        setLoading(false)
      }
    }

    loadHealth()
    // Refresh health status every 30 seconds
    const interval = setInterval(loadHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const getOverallStatus = () => {
    if (!health) return 'unknown'
    const services = health.services || {}
    const hasUnhealthy = Object.values(services).some((s: any) => !s.healthy)
    return hasUnhealthy ? 'warning' : 'healthy'
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-3 w-3 text-green-600" />
      case 'warning':
        return <AlertTriangle className="h-3 w-3 text-yellow-600" />
      case 'error':
        return <XCircle className="h-3 w-3 text-red-600" />
      default:
        return <Activity className="h-3 w-3 text-gray-600" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-2">
        <Activity className="h-3 w-3 animate-pulse" />
        <span className="text-xs">Checking...</span>
      </div>
    )
  }

  const overallStatus = getOverallStatus()

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={`h-6 px-2 text-xs ${getStatusColor(overallStatus)}`}
        >
          {getStatusIcon(overallStatus)}
          <span className="ml-1">System</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80" align="end">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">System Health</h4>
            <Badge variant={overallStatus === 'healthy' ? 'default' : 'destructive'}>
              {overallStatus === 'healthy' ? 'All Good' : 'Issues Detected'}
            </Badge>
          </div>

          <div className="space-y-2">
            {health?.services && Object.entries(health.services).map(([service, status]: [string, any]) => (
              <div key={service} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  {status.healthy ? (
                    <CheckCircle className="h-3 w-3 text-green-600" />
                  ) : (
                    <XCircle className="h-3 w-3 text-red-600" />
                  )}
                  <span className="capitalize">{service.replace('_', ' ')}</span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {status.response_time ? `${status.response_time}ms` : 'N/A'}
                </span>
              </div>
            ))}
          </div>

          <div className="text-xs text-muted-foreground pt-2 border-t">
            Last updated: {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : 'Unknown'}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}