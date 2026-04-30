'use client';

import React from 'react';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { cn } from '@/lib/utils';
import { useSidebarStore } from '@/stores/sidebar-store';
import { AppSidebar } from '@/components/layout/app-sidebar';
import { TopBar } from '@/components/layout/top-bar';
import { ChatPanel } from '@/components/layout/chat-panel';

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
 *
 * The ChatPanel is rendered inline on the right side of the content area.
 * When toggled open it pushes the main content to the left via CSS transitions.
 */
function DashboardLayoutClient({ children }: DashboardLayoutClientProps) {
  const { isChatPanelOpen, toggleChatPanel } = useSidebarStore();

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
        <div className="flex flex-1 overflow-hidden">
          {/* Main content area -- shrinks when chat panel is open */}
          <div className="flex flex-1 flex-col min-w-0 transition-all duration-300 ease-in-out">
            <div className="@container/main flex flex-1 flex-col gap-2">
              {children}
            </div>
          </div>

          {/* Inline chat panel -- pushes content when open */}
          <div
            className={cn(
              'shrink-0 border-l bg-background transition-all duration-300 ease-in-out overflow-hidden',
              isChatPanelOpen ? 'w-[400px] lg:w-[480px]' : 'w-0 border-l-0'
            )}
          >
            {isChatPanelOpen && (
              <div className="h-full w-[400px] lg:w-[480px]">
                <ChatPanel onClose={toggleChatPanel} />
              </div>
            )}
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

export default DashboardLayoutClient;
