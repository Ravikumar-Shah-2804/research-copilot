"use client"

import { useState } from "react"
import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { RouteGuard } from "@/components/auth/RouteGuard"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useAuth } from "@/lib/auth-context"
import { Loader2 } from "lucide-react"

function SettingsForm() {
  const { user, logout } = useAuth()
  const [isDeleting, setIsDeleting] = useState(false)
  const [message, setMessage] = useState("")

  const handleDeleteAccount = async () => {
    if (!confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
      return
    }

    setIsDeleting(true)
    setMessage("")

    try {
      // TODO: Implement account deletion API call when available
      setMessage("Account deletion functionality will be implemented when the backend API is ready.")
    } catch (error: any) {
      setMessage(error.detail || "Failed to delete account.")
    } finally {
      setIsDeleting(false)
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
        <h1 className="text-xl font-semibold">Settings</h1>

        {message && (
          <Alert>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Appearance</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <div>
              <div className="font-medium">Dark mode</div>
              <div className="text-sm text-muted-foreground">Toggle dark theme</div>
            </div>
            <Switch />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Account</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2">Account Information</h4>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Username: {user.username}</p>
                <p>Email: {user.email}</p>
                <p>Role: {user.is_superuser ? 'Administrator' : 'User'}</p>
              </div>
            </div>
            <div className="pt-4 border-t">
              <Button
                variant="destructive"
                onClick={handleDeleteAccount}
                disabled={isDeleting}
              >
                {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Delete account
              </Button>
              <p className="text-xs text-muted-foreground mt-2">
                This action cannot be undone. All your data will be permanently deleted.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </SidebarNav>
  )
}

export default function SettingsPage() {
  return (
    <RouteGuard requireAuth={true}>
      <SettingsForm />
    </RouteGuard>
  )
}