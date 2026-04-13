'use client';

import { MessageSquare } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { SidebarTrigger } from '@/components/ui/sidebar';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { ThemeToggle } from './theme-toggle';
import { LanguageSwitcher } from './language-switcher';
import { ChatPanel } from './chat-panel';

interface TopBarProps {
  /** Optional breadcrumb title for the current page */
  breadcrumb?: string;
}

/**
 * TopBar — Sticky application header bar.
 *
 * Height: 56px (h-14 / 3.5rem), sticky top-0, z-40.
 * Left: SidebarTrigger + Separator + Breadcrumb
 * Right: ThemeToggle + LanguageSwitcher + ChatPanel Sheet trigger
 *
 * User menu has moved to the sidebar footer (shadcn dashboard-01 pattern).
 */
export function TopBar({ breadcrumb }: TopBarProps) {
  const tChat = useTranslations('Chat');

  return (
    <header className="flex h-14 items-center gap-2 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 sticky top-0 z-40">
      {/* Left side: sidebar trigger + breadcrumb */}
      <div className="flex flex-1 items-center gap-2 min-w-0">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/dashboard">PAPERY</BreadcrumbLink>
            </BreadcrumbItem>
            {breadcrumb && (
              <>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>{breadcrumb}</BreadcrumbPage>
                </BreadcrumbItem>
              </>
            )}
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      {/* Right side: actions */}
      <div className="flex items-center gap-1">
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
    </header>
  );
}
