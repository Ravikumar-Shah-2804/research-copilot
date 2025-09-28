"use client"

import { SidebarNav } from "@/components/research-copilot/SidebarNav"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"

export default function ScholarsPage(){
  const scholars = [
    { name: "Yann LeCun", field: "Representation learning", img: "https://images.unsplash.com/photo-1547425260-76bcadfb4f2c?q=80&w=256&auto=format&fit=crop" },
    { name: "Geoffrey Hinton", field: "Deep learning", img: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=256&auto=format&fit=crop" },
    { name: "Yoshua Bengio", field: "Generative models", img: "https://images.unsplash.com/photo-1527980965255-d3b416303d12?q=80&w=256&auto=format&fit=crop" },
  ]
  return (
    <SidebarNav>
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-xl font-semibold">Scholars</h1>
          <p className="text-sm text-muted-foreground">Discover researchers and their work.</p>
        </div>
        <Input placeholder="Search scholars" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {scholars.map((s)=> (
            <Card key={s.name}>
              <CardContent className="p-4 flex items-center gap-3">
                <img alt={s.name} src={s.img} className="size-12 rounded-full object-cover" />
                <div>
                  <div className="font-medium">{s.name}</div>
                  <div className="text-sm text-muted-foreground">{s.field}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </SidebarNav>
  )
}