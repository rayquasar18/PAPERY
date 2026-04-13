'use client';

import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/layout/app-sidebar';
import { TopBar } from '@/components/layout/top-bar';

interface DashboardLayoutClientProps {
  children: React.ReactNode;
}

/**
 * DashboardLayoutClient — Client shell for the dashboard route group.
 *
 * Uses the shadcn dashboard-01 pattern:
 * SidebarProvider > AppSidebar + SidebarInset (main content wrapper).
 * Chat panel is rendered as a Sheet overlay from the TopBar.
 */
function DashboardLayoutClient({ children }: DashboardLayoutClientProps) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <TopBar />
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

export default DashboardLayoutClient;
