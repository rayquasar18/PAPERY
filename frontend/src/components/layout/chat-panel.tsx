'use client';

import { X, Bot } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useSidebarStore } from '@/lib/stores/sidebar-store';

/**
 * ChatPanel — Right-side AI assistant panel.
 *
 * v1 placeholder: shows "AI Assistant coming soon" message.
 * Full QuasarFlow integration in a future phase.
 * Uses ScrollArea for content area to support future chat message list.
 */
export function ChatPanel() {
  const t = useTranslations('Chat');
  const { toggleChatPanel } = useSidebarStore();

  return (
    <div className="flex h-full flex-col bg-background border-l">
      {/* Panel header */}
      <div className="flex h-14 items-center justify-between px-4 border-b shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="size-4 text-primary" />
          <span className="font-semibold text-sm">{t('placeholder.title')}</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="size-8"
          onClick={toggleChatPanel}
          aria-label="Close chat panel"
        >
          <X className="size-4" />
        </Button>
      </div>

      {/* Scrollable content area */}
      <ScrollArea className="flex-1">
        <div className="flex flex-col items-center justify-center h-full min-h-64 gap-4 p-8 text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-primary/10">
            <Bot className="size-7 text-primary" />
          </div>
          <div className="space-y-1.5">
            <p className="font-semibold text-sm">{t('placeholder.title')}</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {t('placeholder.body')}
            </p>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
