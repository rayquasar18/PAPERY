'use client';

import { MessageSquare } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { SidebarTrigger } from '@/components/ui/sidebar';
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { ThemeToggle } from './theme-toggle';
import { LanguageSwitcher } from './language-switcher';
import { ChatPanel } from './chat-panel';

/**
 * TopBar -- Sticky application header adapted from shadcn dashboard-01 site-header.
 *
 * Uses the exact CSS structure from shadcn site-header:
 * flex h-(--header-height) shrink-0 items-center gap-2 border-b
 *
 * Left side: SidebarTrigger + Separator + page title
 * Right side: ThemeToggle + LanguageSwitcher + ChatPanel Sheet trigger
 * User avatar is in the sidebar footer only (NavUser component).
 */
export function TopBar() {
  const tChat = useTranslations('Chat');

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
          <Sheet>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-9"
                aria-label="Toggle AI chat panel"
              >
                <MessageSquare className="size-4" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[400px] sm:w-[540px] p-0">
              <SheetTitle className="sr-only">{tChat('placeholder.title')}</SheetTitle>
              <ChatPanel />
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
