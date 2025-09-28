"use client"

import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function HistoryPage(){
  const items = [
    { id: 1, title: "Summarize: Attention Is All You Need", ts: "Today" },
    { id: 2, title: "Search: protein structure prediction", ts: "Yesterday" },
    { id: 3, title: "Chat: pros/cons of RAG", ts: "2 days ago" },
  ]
  return (
    <SidebarNav>
      <div className="p-6 space-y-6">
        <h1 className="text-xl font-semibold">History</h1>
        <div className="grid gap-3">
          {items.map((it)=> (
            <Card key={it.id}>
              <CardHeader className="py-3">
                <CardTitle className="text-base">{it.title}</CardTitle>
              </CardHeader>
              <CardContent className="pt-0 pb-3 text-sm text-muted-foreground">{it.ts}</CardContent>
            </Card>
          ))}
        </div>
      </div>
    </SidebarNav>
  )
}