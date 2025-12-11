'use client';

import { Plus, MessageSquare, Trash2, Check, X } from 'lucide-react';
import { useState } from 'react';
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

function SessionItem({ session, isActive }: { session: ChatSession; isActive: boolean }) {
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
      onClick={() => switchSession(session.id)}
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

export function ChatHistory() {
  const { sessions, currentSessionId, createSession } = useChatStore();

  return (
    <div className="w-56 flex flex-col h-full">
      <div className="p-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 h-8 text-xs"
          onClick={() => createSession()}
        >
          <Plus className="h-3.5 w-3.5" />
          New Chat
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-2 pb-2 space-y-0.5">
          {sessions.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-8 px-4">
              Start a conversation
            </p>
          ) : (
            sessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                isActive={session.id === currentSessionId}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
