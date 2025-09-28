"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { adminAPI } from "@/lib/api/admin"
import { SearchStats } from "@/types/api"
import { RotateCcw, Loader2, Database } from "lucide-react"

interface IndexManagementCardProps {
  stats: SearchStats | null
}

export function IndexManagementCard({ stats }: IndexManagementCardProps) {
  const [isRebuilding, setIsRebuilding] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  const handleRebuildIndex = async () => {
    try {
      setIsRebuilding(true)
      setMessage(null)

      const result = await adminAPI.rebuildSearchIndex()
      setMessage(`Index rebuild ${result.status}: ${result.message}`)
      setIsDialogOpen(false)
    } catch (error: any) {
      setMessage(error.detail || "Failed to rebuild search index")
    } finally {
      setIsRebuilding(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Search Index Management
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {stats && (
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium">{stats.total_queries.toLocaleString()}</p>
              <p className="text-muted-foreground">Total Queries</p>
            </div>
            <div>
              <p className="font-medium">{stats.average_query_time.toFixed(2)}ms</p>
              <p className="text-muted-foreground">Avg Query Time</p>
            </div>
            <div>
              <p className="font-medium">{(stats.search_success_rate * 100).toFixed(1)}%</p>
              <p className="text-muted-foreground">Success Rate</p>
            </div>
            <div>
              <p className="font-medium">{stats.index_size.toLocaleString()}</p>
              <p className="text-muted-foreground">Index Size</p>
            </div>
          </div>
        )}

        <p className="text-sm text-muted-foreground">
          Rebuild the search index from scratch. This operation may take several minutes
          and will temporarily make search unavailable.
        </p>

        {message && (
          <Alert variant={message.includes("success") || message.includes("completed") ? "default" : "destructive"}>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <AlertDialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" className="w-full">
              <RotateCcw className="h-4 w-4 mr-2" />
              Rebuild Search Index
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Rebuild Search Index</AlertDialogTitle>
              <AlertDialogDescription>
                This action will rebuild the entire search index from scratch. This operation may take
                several minutes to complete and will temporarily make search functionality unavailable.
                <br /><br />
                During this process, users will not be able to perform searches. Are you sure you want to proceed?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleRebuildIndex}
                disabled={isRebuilding}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {isRebuilding && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Rebuild Index
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  )
}