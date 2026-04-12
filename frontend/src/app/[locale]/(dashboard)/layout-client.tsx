'use client';

import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { SidebarProvider } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/layout/app-sidebar';
import { TopBar } from '@/components/layout/top-bar';
import { ChatPanel } from '@/components/layout/chat-panel';
import { useSidebarStore } from '@/lib/stores/sidebar-store';

interface DashboardLayoutClientProps {
  children: React.ReactNode;
}

/**
 * DashboardLayoutClient — Client shell for the dashboard route group.
 *
 * Wraps children in SidebarProvider + AppSidebar + TopBar + ResizablePanelGroup.
 * ResizablePanelGroup splits main content from the optional chat panel (D-05).
 * Chat panel visibility is driven by Zustand isChatPanelOpen state.
 *
 * Note: react-resizable-panels v4 uses aria-orientation instead of direction prop.
 * Horizontal layout is the default; set via aria-orientation on the wrapper.
 */
function DashboardLayoutClient({ children }: DashboardLayoutClientProps) {
  const { isChatPanelOpen } = useSidebarStore();

  return (
    <SidebarProvider>
      <AppSidebar />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopBar />
        <ResizablePanelGroup
          className="flex-1"
          orientation="horizontal"
        >
          {/* Main content panel */}
          <ResizablePanel defaultSize={isChatPanelOpen ? 70 : 100} minSize={40}>
            <main id="main-content" className="h-full overflow-auto">
              {children}
            </main>
          </ResizablePanel>

          {/* Chat panel — conditionally rendered */}
          {isChatPanelOpen && (
            <>
              <ResizableHandle withHandle aria-label="Resize chat panel" />
              <ResizablePanel defaultSize={30} minSize={20} maxSize={50}>
                <ChatPanel />
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
      </div>
    </SidebarProvider>
  );
}

export default DashboardLayoutClient;
