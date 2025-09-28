"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { RouteGuard } from "@/components/auth/RouteGuard"
import AcademicSearchDialog from "@/components/research-copilot/AcademicSearchDialog"

function HomeContent() {
  return (
    <SidebarNav>
      <div className="p-6">
        <div className="rounded-lg border bg-card p-6 grid gap-6 md:grid-cols-2">
          <div className="space-y-3">
            <h1 className="text-2xl font-semibold">Welcome to Research Copilot</h1>
            <p className="text-muted-foreground">A minimal, fast, accessible workspace to search, chat, and manage academic sources.</p>
            <div className="flex gap-2">
              <Link href="/chat"><Button>Open Chat</Button></Link>
              <AcademicSearchDialog />
            </div>
          </div>
          <div className="rounded-md overflow-hidden">
            <img alt="Calm abstract orchid gradient" className="h-full w-full object-cover" src="https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1600&auto=format&fit=crop" />
          </div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border p-4">
            <h3 className="font-medium">Quick search</h3>
            <p className="text-sm text-muted-foreground mb-3">Jump right into papers.</p>
            <div className="flex gap-2">
              <Input placeholder="e.g., Diffusion models for RL" />
              <AcademicSearchDialog triggerClassName="hidden" />
              <Link href="/chat"><Button variant="outline">Ask Copilot</Button></Link>
            </div>
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="font-medium">Your Library</h3>
            <p className="text-sm text-muted-foreground mb-3">Organize collections and sources.</p>
            <Link href="/explore/library"><Button variant="outline">Open Library</Button></Link>
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="font-medium">Knowledge Base</h3>
            <p className="text-sm text-muted-foreground mb-3">Curated notes and summaries.</p>
            <Link href="/explore/knowledge-base"><Button variant="outline">Explore</Button></Link>
          </div>
        </div>
      </div>
    </SidebarNav>
  )
}

export default function Home() {
  return (
    <RouteGuard requireAuth={true}>
      <HomeContent />
    </RouteGuard>
  )
}