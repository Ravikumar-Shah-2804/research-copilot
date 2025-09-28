"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { UserStats } from "@/types/api"
import { Users, UserCheck, UserPlus, TrendingUp } from "lucide-react"

interface UserManagementCardProps {
  stats: UserStats | null
}

export function UserManagementCard({ stats }: UserManagementCardProps) {
  if (!stats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            User Management
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading user statistics...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          User Management
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-green-500" />
            <div>
              <p className="text-sm font-medium">{stats.active_users.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">Active Users</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <UserPlus className="h-4 w-4 text-blue-500" />
            <div>
              <p className="text-sm font-medium">{stats.new_users_today}</p>
              <p className="text-xs text-muted-foreground">New Today</p>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t">
          <h4 className="text-sm font-medium mb-2">Top Search Queries</h4>
          <div className="space-y-1">
            {Object.entries(stats.top_search_queries).slice(0, 3).map(([query, count]) => (
              <div key={query} className="flex items-center justify-between text-xs">
                <span className="truncate max-w-[200px] text-muted-foreground">{query}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground">
            Advanced user management features (user deactivation, role changes, etc.) will be available in future updates.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}