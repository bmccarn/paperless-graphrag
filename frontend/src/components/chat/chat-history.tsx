'use client';

import { Plus, MessageSquare, Trash2, Check, X } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useChatStore, type ChatSession } from '@/lib/stores/chat-store';

function formatDate(date: Date): string {
  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 7) return `${diffDays}d`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

interface SessionItemProps {
  session: ChatSession;
  isActive: boolean;
  onSelect?: () => void;
}

function SessionItem({ session, isActive, onSelect }: SessionItemProps) {
  const { switchSession, renameSession, deleteSession } = useChatStore();
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(session.name);

  const handleSave = () => {
    if (editName.trim()) {
      renameSession(session.id, editName.trim());
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditName(session.name);
    setIsEditing(false);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSession(session.id);
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-1 p-2 rounded-md bg-muted">
        <Input
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          className="h-7 text-xs"
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSave();
            if (e.key === 'Escape') handleCancel();
          }}
        />
        <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={handleSave}>
          <Check className="h-3 w-3" />
        </Button>
        <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={handleCancel}>
          <X className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'group flex items-start gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors',
        isActive ? 'bg-primary/10' : 'hover:bg-muted/50'
      )}
      onClick={() => {
        switchSession(session.id);
        onSelect?.();
      }}
      onDoubleClick={() => setIsEditing(true)}
    >
      <MessageSquare className={cn('h-3.5 w-3.5 mt-0.5 shrink-0', isActive ? 'text-primary' : 'text-muted-foreground')} />
      <div className="flex-1 min-w-0">
        <p className={cn('text-xs truncate', isActive ? 'font-medium' : '')}>{session.name}</p>
        <p className="text-[10px] text-muted-foreground">
          {formatDate(session.updatedAt)}
        </p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 text-muted-foreground hover:text-destructive"
        onClick={handleDelete}
      >
        <Trash2 className="h-3 w-3" />
      </Button>
    </div>
  );
}

interface ChatHistoryProps {
  onSelectConversation?: () => void;
}

export function ChatHistory({ onSelectConversation }: ChatHistoryProps) {
  // Handle hydration - wait for client-side state to be ready
  const [isHydrated, setIsHydrated] = useState(false);

  const { sessions, currentSessionId, createSession, checkDbStatus, initFromDatabase } = useChatStore();

  useEffect(() => {
    setIsHydrated(true);

    // Initialize database status and sync sessions
    const initDb = async () => {
      await checkDbStatus();
      await initFromDatabase();
    };
    initDb();
  }, [checkDbStatus, initFromDatabase]);

  const handleCreateSession = () => {
    createSession();
    onSelectConversation?.();
  };

  // Don't render sessions list until hydrated to avoid mismatch
  const displaySessions = isHydrated ? sessions : [];

  return (
    <div className="w-full lg:w-56 flex flex-col h-full">
      <div className="p-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 h-9 lg:h-8 text-sm lg:text-xs"
          onClick={handleCreateSession}
        >
          <Plus className="h-4 w-4 lg:h-3.5 lg:w-3.5" />
          New Chat
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-2 pb-2 space-y-0.5">
          {displaySessions.length === 0 ? (
            <p className="text-sm lg:text-xs text-muted-foreground text-center py-8 px-4">
              {isHydrated ? 'Start a conversation' : 'Loading...'}
            </p>
          ) : (
            displaySessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                isActive={session.id === currentSessionId}
                onSelect={onSelectConversation}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
