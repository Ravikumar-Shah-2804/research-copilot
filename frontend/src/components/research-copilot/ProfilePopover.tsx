"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth-context"
import { Loader2 } from "lucide-react"

export function ProfilePopover() {
  const { user, logout, isLoading } = useAuth()
  const router = useRouter()

  const handleLogout = async () => {
    try {
      await logout()
      router.push('/login')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  if (!user) {
    return null
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button aria-label="Open profile menu" className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent">
          <Avatar className="size-7">
            <AvatarImage src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=100&auto=format&fit=crop" alt="User" />
            <AvatarFallback>{user.username?.charAt(0).toUpperCase() || 'U'}</AvatarFallback>
          </Avatar>
          <span className="text-sm font-medium hidden md:inline">{user.username || 'User'}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-56">
        <div className="flex items-center gap-3">
          <Avatar className="size-10">
            <AvatarImage src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=100&auto=format&fit=crop" alt="User" />
            <AvatarFallback>{user.username?.charAt(0).toUpperCase() || 'U'}</AvatarFallback>
          </Avatar>
          <div>
            <p className="text-sm font-semibold">{user.full_name || user.username}</p>
            <p className="text-xs text-muted-foreground">{user.email}</p>
          </div>
        </div>
        <div className="my-2 h-px bg-border" />
        <div className="grid gap-1.5 text-sm">
          <Link href="/profile" className="rounded px-2 py-1 hover:bg-accent">Profile</Link>
          <Link href="/settings" className="rounded px-2 py-1 hover:bg-accent">Settings</Link>
          <Link href="/history" className="rounded px-2 py-1 hover:bg-accent">History</Link>
        </div>
        <div className="my-2 h-px bg-border" />
        <Button
          variant="outline"
          className="w-full"
          onClick={handleLogout}
          disabled={isLoading}
        >
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Sign out
        </Button>
      </PopoverContent>
    </Popover>
  )
}

export default ProfilePopover