"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BookOpen, Bot, Database, Library, PanelLeftClose, PanelLeftOpen, Search, Sparkles, Users, BarChart3, Shield } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import ProfilePopover from "./ProfilePopover"
import { HealthIndicator } from "@/components/analytics/HealthIndicator"
import { useAuth } from "@/lib/auth-context"

function NavItem({ href, label, icon: Icon }: { href: string; label: string; icon: any }) {
  const pathname = usePathname()
  const isActive = pathname === href
  return (
    <SidebarMenuItem>
      <Link href={href} passHref legacyBehavior>
        <SidebarMenuButton asChild isActive={isActive} tooltip={label}>
          <a className="flex items-center gap-2">
            <Icon className="size-4" />
            <span>{label}</span>
          </a>
        </SidebarMenuButton>
      </Link>
    </SidebarMenuItem>
  )
}

export function SidebarNav({ children }: { children?: React.ReactNode }) {
  const pathname = usePathname()
  const { user } = useAuth()

  return (
    <SidebarProvider>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <div className="flex items-center gap-2 px-2 py-1.5">
            <Sparkles className="size-5 text-primary" />
            <span className="font-semibold">Research Copilot</span>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Workspace</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <NavItem href="/chat" label="Chat" icon={Bot} />
                <NavItem href="/history" label="History" icon={BookOpen} />
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarSeparator />

          <SidebarGroup>
            <SidebarGroupLabel>Explore</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <NavItem href="/explore/subscription" label="Subscription" icon={Sparkles} />
                <SidebarMenuItem>
                  <SidebarMenuButton tooltip="Library">
                    <div className="flex items-center gap-2"><Library className="size-4" /><span>Library</span></div>
                  </SidebarMenuButton>
                  <SidebarMenuSub>
                    <SidebarMenuSubItem>
                      <Link href="/explore/library" passHref legacyBehavior>
                        <SidebarMenuSubButton asChild size="sm">
                          <a>All Collections</a>
                        </SidebarMenuSubButton>
                      </Link>
                    </SidebarMenuSubItem>
                    <SidebarMenuSubItem>
                      <SidebarMenuSubButton asChild size="sm">
                        <a href="#papers">Papers</a>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  </SidebarMenuSub>
                </SidebarMenuItem>
                <NavItem href="/explore/scholars" label="Scholars" icon={Users} />
                <NavItem href="/explore/knowledge-base" label="Knowledge Base" icon={Database} />
                <NavItem href="/analytics" label="Analytics" icon={BarChart3} />
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          {user?.is_superuser && (
            <>
              <SidebarSeparator />

              <SidebarGroup>
                <SidebarGroupLabel>Administration</SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu>
                    <NavItem href="/admin" label="Admin Dashboard" icon={Shield} />
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            </>
          )}
        </SidebarContent>
        <SidebarFooter>
          <div className="space-y-2 px-2">
            <div className="flex items-center justify-between">
              <ProfilePopover />
              <SidebarTrigger className="ml-auto" aria-label="Toggle sidebar" />
            </div>
            <HealthIndicator />
          </div>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>
      <SidebarInset>
        {children}
      </SidebarInset>
    </SidebarProvider>
  )
}

export default SidebarNav