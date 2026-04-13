'use client';

import React from 'react';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/layout/app-sidebar';
import { TopBar } from '@/components/layout/top-bar';

interface DashboardLayoutClientProps {
  children: React.ReactNode;
}

/**
 * DashboardLayoutClient -- Client shell for the dashboard route group.
 *
 * Adapted from shadcn dashboard-01 page layout pattern:
 * SidebarProvider with CSS custom properties for sidebar width and header height,
 * AppSidebar with variant="inset", SidebarInset wrapping TopBar + content area
 * with @container/main for responsive container queries.
 */
function DashboardLayoutClient({ children }: DashboardLayoutClientProps) {
  return (
    <SidebarProvider
      style={
        {
          '--sidebar-width': 'calc(var(--spacing) * 72)',
          '--header-height': 'calc(var(--spacing) * 12)',
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <TopBar />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            {children}
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

export default DashboardLayoutClient;
