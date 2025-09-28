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
import { Trash2, Loader2 } from "lucide-react"

export function CacheManagementCard() {
  const [isClearing, setIsClearing] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  const handleClearCache = async () => {
    try {
      setIsClearing(true)
      setMessage(null)

      const result = await adminAPI.clearCache()
      setMessage(result.message || "Cache cleared successfully")
      setIsDialogOpen(false)
    } catch (error: any) {
      setMessage(error.detail || "Failed to clear cache")
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Trash2 className="h-5 w-5" />
          Cache Management
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Clear all cached data from the system. This operation will temporarily impact performance
          as data is re-cached on subsequent requests.
        </p>

        {message && (
          <Alert variant={message.includes("successfully") ? "default" : "destructive"}>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <AlertDialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" className="w-full">
              <Trash2 className="h-4 w-4 mr-2" />
              Clear All Cache
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear All Cache</AlertDialogTitle>
              <AlertDialogDescription>
                This action will clear all cached data from the system. This operation cannot be undone
                and may temporarily impact system performance as data is re-cached.
                <br /><br />
                Are you sure you want to proceed?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleClearCache}
                disabled={isClearing}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {isClearing && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Clear Cache
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  )
}