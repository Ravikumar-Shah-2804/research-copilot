"use client"

import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function KnowledgeBasePage(){
  return (
    <SidebarNav>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Knowledge Base</h1>
          <Button variant="outline">New Note</Button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {["Diffusion 101","Graph Transformers","CASP14 Notes"].map((t)=> (
            <Card key={t}>
              <CardHeader>
                <CardTitle className="text-base">{t}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Short summary placeholder for {t}.</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </SidebarNav>
  )
}