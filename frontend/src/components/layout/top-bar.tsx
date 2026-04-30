'use client';

import { MessageSquare } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { cn } from '@/lib/utils';
import { useSidebarStore } from '@/stores/sidebar-store';
import { ThemeToggle } from './theme-toggle';
import { LanguageSwitcher } from './language-switcher';

/**
 * TopBar -- Sticky application header adapted from shadcn dashboard-01 site-header.
 *
 * Uses the exact CSS structure from shadcn site-header:
 * flex h-(--header-height) shrink-0 items-center gap-2 border-b
 *
 * Left side: SidebarTrigger + Separator + page title
 * Right side: ThemeToggle + LanguageSwitcher + Chat toggle button
 * User avatar is in the sidebar footer only (NavUser component).
 *
 * The chat toggle button controls `isChatPanelOpen` in the sidebar store.
 * The ChatPanel itself is rendered inline in layout-client.tsx (not here).
 */
export function TopBar() {
  const { isChatPanelOpen, toggleChatPanel } = useSidebarStore();

  return (
    <header className="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        {/* Left side: sidebar trigger + separator + page title */}
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 data-[orientation=vertical]:h-4"
        />
        <h1 className="text-base font-medium">Documents</h1>

        {/* Right side: actions */}
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <LanguageSwitcher />
          <Button
            variant="ghost"
            size="icon"
            className={cn('size-9', isChatPanelOpen && 'bg-accent text-accent-foreground')}
            onClick={toggleChatPanel}
            aria-label="Toggle AI chat panel"
            aria-pressed={isChatPanelOpen}
          >
            <MessageSquare className="size-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
