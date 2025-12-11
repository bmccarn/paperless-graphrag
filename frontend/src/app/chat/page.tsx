'use client';

import { ChatHeader, MessageList, ChatInput, ChatHistory } from '@/components/chat';

export default function ChatPage() {
  return (
    <div className="h-[calc(100vh-9rem)] flex gap-6">
      {/* Chat History Sidebar */}
      <div className="hidden lg:flex flex-col bg-muted/30 rounded-lg">
        <ChatHistory />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatHeader />
        <div className="flex-1 flex flex-col min-h-0 mt-4">
          <MessageList />
          <div className="pt-4 mt-4">
            <ChatInput />
          </div>
        </div>
      </div>
    </div>
  );
}
