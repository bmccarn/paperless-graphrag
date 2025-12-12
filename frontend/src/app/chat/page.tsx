'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { History, X, Loader2 } from 'lucide-react';

// Dynamically import components that use persisted store to avoid hydration mismatch
const ChatHeader = dynamic(
  () => import('@/components/chat').then((mod) => mod.ChatHeader),
  { ssr: false }
);

const MessageList = dynamic(
  () => import('@/components/chat').then((mod) => mod.MessageList),
  {
    ssr: false,
    loading: () => (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }
);

const ChatInput = dynamic(
  () => import('@/components/chat').then((mod) => mod.ChatInput),
  { ssr: false }
);

const ChatHistory = dynamic(
  () => import('@/components/chat').then((mod) => mod.ChatHistory),
  { ssr: false }
);

export default function ChatPage() {
  const [historyOpen, setHistoryOpen] = useState(false);

  return (
    <div className="h-[calc(100vh-7rem)] md:h-[calc(100vh-9rem)] flex gap-4 md:gap-6 relative">
      {/* Mobile History Toggle Button */}
      <Button
        variant="outline"
        size="sm"
        className="lg:hidden absolute top-0 right-0 z-10 h-9"
        onClick={() => setHistoryOpen(true)}
      >
        <History className="h-4 w-4 mr-2" />
        History
      </Button>

      {/* Mobile Chat History Drawer */}
      {historyOpen && (
        <>
          {/* Backdrop */}
          <div
            className="lg:hidden fixed inset-0 bg-black/50 z-40"
            onClick={() => setHistoryOpen(false)}
          />
          {/* Drawer */}
          <div className="lg:hidden fixed inset-y-0 left-0 w-80 max-w-[85vw] bg-background z-50 flex flex-col shadow-xl">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="font-semibold">Chat History</h2>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setHistoryOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-hidden">
              <ChatHistory onSelectConversation={() => setHistoryOpen(false)} />
            </div>
          </div>
        </>
      )}

      {/* Desktop Chat History Sidebar */}
      <div className="hidden lg:flex flex-col bg-muted/30 rounded-lg">
        <ChatHistory />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatHeader />
        <div className="flex-1 flex flex-col min-h-0 mt-2 md:mt-4">
          <MessageList />
          <div className="pt-2 md:pt-4 mt-2 md:mt-4">
            <ChatInput />
          </div>
        </div>
      </div>
    </div>
  );
}
