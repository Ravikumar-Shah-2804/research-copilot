"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SystemStats } from "@/types/api"
import { Database, Users, Search, Clock, TrendingUp } from "lucide-react"

interface SystemStatsCardProps {
  stats: SystemStats | null
}

export function SystemStatsCard({ stats }: SystemStatsCardProps) {
  if (!stats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            System Statistics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading system statistics...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          System Statistics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-blue-500" />
            <div>
              <p className="text-sm font-medium">{stats.total_users.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">Total Users</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-green-500" />
            <div>
              <p className="text-sm font-medium">{stats.total_papers.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">Total Papers</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-purple-500" />
            <div>
              <p className="text-sm font-medium">{stats.total_searches.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">Total Searches</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-orange-500" />
            <div>
              <p className="text-sm font-medium">{(stats.cache_hit_rate * 100).toFixed(1)}%</p>
              <p className="text-xs text-muted-foreground">Cache Hit Rate</p>
            </div>
          </div>
        </div>
        <div className="pt-2 border-t">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-gray-500" />
            <div>
              <p className="text-sm font-medium">{stats.average_response_time.toFixed(2)}ms</p>
              <p className="text-xs text-muted-foreground">Avg Response Time</p>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-muted-foreground">
              System Uptime: {Math.floor(stats.system_uptime / 3600)}h {Math.floor((stats.system_uptime % 3600) / 60)}m
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}