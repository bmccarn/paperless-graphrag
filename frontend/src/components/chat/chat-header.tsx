'use client';

import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { QuerySettings } from './query-settings';
import { MethodSelector } from './method-selector';
import { useChatStore } from '@/lib/stores';

export function ChatHeader() {
  const { messages: getMessages, clearHistory } = useChatStore();
  const messageList = getMessages();

  return (
    <div className="flex items-center justify-between pb-4 border-b border-border/50">
      <MethodSelector />
      <div className="flex items-center gap-2">
        {messageList.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearHistory}
            className="text-muted-foreground hover:text-foreground"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
        <QuerySettings />
      </div>
    </div>
  );
}
