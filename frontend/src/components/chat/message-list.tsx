'use client';

import { useEffect, useState, useRef } from 'react';
import { MessageItem } from './message-item';
import { useChatStore } from '@/lib/stores';
import { Loader2, Brain, Search, Sparkles, Database, Network, FileText } from 'lucide-react';

// Get appropriate icon for the current thinking stage
function getThinkingIcon(message?: string) {
  if (!message) return <Brain className="h-4 w-4 text-primary animate-pulse" />;

  const msg = message.toLowerCase();
  if (msg.includes('generat') || msg.includes('synthes')) {
    return <Sparkles className="h-4 w-4 text-primary animate-pulse" />;
  }
  if (msg.includes('search') || msg.includes('finding') || msg.includes('query')) {
    return <Search className="h-4 w-4 text-primary animate-pulse" />;
  }
  if (msg.includes('load') || msg.includes('read')) {
    return <Database className="h-4 w-4 text-primary animate-pulse" />;
  }
  if (msg.includes('context') || msg.includes('gather') || msg.includes('merg')) {
    return <Network className="h-4 w-4 text-primary animate-pulse" />;
  }
  if (msg.includes('communit') || msg.includes('report')) {
    return <FileText className="h-4 w-4 text-primary animate-pulse" />;
  }
  if (msg.includes('embed') || msg.includes('vector')) {
    return <Brain className="h-4 w-4 text-primary animate-pulse" />;
  }
  return <Brain className="h-4 w-4 text-primary animate-pulse" />;
}

export function MessageList() {
  // Handle hydration - wait for client-side state to be ready
  const [isHydrated, setIsHydrated] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  const isLoading = useChatStore((state) => state.isLoading);
  const thinking = useChatStore((state) => state.thinking);
  const sessions = useChatStore((state) => state.sessions);
  const currentSessionId = useChatStore((state) => state.currentSessionId);

  // Get messages from current session
  const messages = sessions.find(s => s.id === currentSessionId)?.messages || [];

  // Auto-scroll to bottom when messages change or loading state changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, isLoading, thinking]);

  // Show placeholder during hydration to avoid mismatch
  if (!isHydrated) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md">
          <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
          <p className="text-muted-foreground text-sm">Loading chat...</p>
        </div>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md">
          <h3 className="text-lg font-semibold">Ask anything about your documents</h3>
          <p className="text-muted-foreground text-sm">
            Use natural language to search through your Paperless documents.
            Try questions like &quot;What invoices did I receive from Amazon?&quot; or
            &quot;Summarize my tax documents from 2024&quot;.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto pr-4">
      <div className="space-y-4 pb-4 px-4">
        {messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="flex gap-4 p-4 rounded-lg bg-gradient-to-r from-primary/5 to-transparent border border-primary/10">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
              {getThinkingIcon(thinking?.message)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm">GraphRAG</span>
                <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
              </div>
              <p className="text-sm text-primary font-medium mt-1">
                {thinking?.message || 'Processing...'}
              </p>
              {thinking?.detail && (
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  {thinking.detail}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
