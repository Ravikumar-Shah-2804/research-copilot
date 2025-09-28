"use client"

import Link from "next/link"
import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { Button } from "@/components/ui/button"

export default function SubscriptionPage(){
  return (
    <SidebarNav>
      <div className="p-6 space-y-4">
        <div className="rounded-lg border bg-card p-6">
          <h1 className="text-xl font-semibold mb-1">Subscription</h1>
          <p className="text-sm text-muted-foreground mb-4">Unlock faster search, premium models, and larger context.</p>
          <div className="flex gap-2">
            <Button>Upgrade</Button>
            <Link href="/chat"><Button variant="outline">Try Chat</Button></Link>
          </div>
        </div>
      </div>
    </SidebarNav>
  )
}