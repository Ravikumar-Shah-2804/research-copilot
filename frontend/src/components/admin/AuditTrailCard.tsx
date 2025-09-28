import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { analyticsAPI } from "@/lib/api/analytics"
import { Loader2, Shield, RefreshCw } from "lucide-react"
import { toast } from "sonner"

interface AuditEvent {
  id: string
  user_id: string
  username?: string
  event_type: string
  event_description: string
  ip_address?: string
  user_agent?: string
  timestamp: string
  details?: Record<string, any>
}

export function AuditTrailCard() {
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadAuditTrail = async (showLoading = true) => {
    try {
      if (showLoading) setIsLoading(true)
      else setIsRefreshing(true)

      const events = await analyticsAPI.getAuditTrail({ limit: 50 })
      setAuditEvents(events)
    } catch (error: any) {
      toast.error("Failed to load audit trail: " + error.detail)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    loadAuditTrail()
  }, [])

  const getEventTypeColor = (eventType: string) => {
    switch (eventType.toLowerCase()) {
      case 'login':
      case 'logout':
        return 'bg-blue-100 text-blue-800'
      case 'create':
      case 'update':
        return 'bg-green-100 text-green-800'
      case 'delete':
        return 'bg-red-100 text-red-800'
      case 'security':
      case 'failed_login':
        return 'bg-orange-100 text-orange-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Audit Trail
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Audit Trail
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadAuditTrail(false)}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96">
          <div className="space-y-3">
            {auditEvents.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No audit events found
              </p>
            ) : (
              auditEvents.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-3 p-3 border rounded-lg bg-muted/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant="secondary"
                        className={getEventTypeColor(event.event_type)}
                      >
                        {event.event_type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(event.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm font-medium">{event.event_description}</p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                      <span>User: {event.username || event.user_id}</span>
                      {event.ip_address && <span>IP: {event.ip_address}</span>}
                    </div>
                    {event.details && Object.keys(event.details).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs cursor-pointer text-muted-foreground hover:text-foreground">
                          Show details
                        </summary>
                        <pre className="text-xs mt-1 bg-background p-2 rounded border overflow-x-auto">
                          {JSON.stringify(event.details, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}