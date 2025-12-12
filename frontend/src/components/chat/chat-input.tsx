'use client';

import { useCallback } from 'react';
import { Send, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
  PromptInputAction,
} from '@/components/ui/prompt-input';
import { useChatStore } from '@/lib/stores';
import { submitQueryStream } from '@/lib/api';
import { toast } from 'sonner';
import type { ConversationMessage } from '@/types';

export function ChatInput() {
  // Use selectors for reactive state
  const isLoading = useChatStore((state) => state.isLoading);
  const selectedMethod = useChatStore((state) => state.selectedMethod);
  const communityLevel = useChatStore((state) => state.communityLevel);
  const input = useChatStore((state) => state.input);
  const sessions = useChatStore((state) => state.sessions);
  const currentSessionId = useChatStore((state) => state.currentSessionId);

  const handleSubmit = useCallback(async () => {
    const store = useChatStore.getState();
    const currentInput = store.input;

    if (!currentInput.trim() || store.isLoading) return;

    const userMessage = currentInput.trim();
    store.setInput('');

    // Get current messages for conversation history (before adding new message)
    const currentSession = store.sessions.find(s => s.id === store.currentSessionId);
    const currentMessages = currentSession?.messages || [];

    // Add user message
    store.addMessage({
      role: 'user',
      content: userMessage,
    });

    store.setLoading(true);
    store.setThinking({ message: 'Starting...', detail: 'Preparing query' });

    // Build conversation history from recent messages (last 6)
    const conversationHistory: ConversationMessage[] = currentMessages
      .slice(-6)
      .map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

    try {
      const response = await submitQueryStream(
        {
          query: userMessage,
          method: store.selectedMethod,
          community_level: store.communityLevel,
          conversation_history: conversationHistory.length > 0 ? conversationHistory : undefined,
        },
        (event) => {
          // Update thinking state based on events - use getState() for fresh reference
          if (event.type === 'status' || event.type === 'thinking') {
            useChatStore.getState().setThinking({
              message: event.message || 'Processing...',
              detail: event.detail,
            });
          }
        }
      );

      useChatStore.getState().addMessage({
        role: 'assistant',
        content: response.response,
        method: store.selectedMethod,
        sourceDocuments: response.source_documents,
      });
    } catch (error) {
      toast.error('Failed to get response', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      useChatStore.getState().addMessage({
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
      });
    } finally {
      useChatStore.getState().setLoading(false);
      useChatStore.getState().setThinking(null);
    }
  }, []);

  // Get setInput for the PromptInput component
  const setInput = useChatStore((state) => state.setInput);

  return (
    <PromptInput
      value={input}
      onValueChange={setInput}
      isLoading={isLoading}
      onSubmit={handleSubmit}
      className="w-full bg-card border-border/50 shadow-sm"
    >
      <PromptInputTextarea
        placeholder="Ask a question about your documents..."
        className="min-h-[44px]"
      />
      <PromptInputActions className="justify-end px-2 pb-2">
        <PromptInputAction tooltip={isLoading ? 'Stop' : 'Send message'}>
          <Button
            onClick={handleSubmit}
            disabled={!input.trim() && !isLoading}
            size="icon"
            className="h-9 w-9 rounded-full"
            variant={isLoading ? 'destructive' : 'default'}
          >
            {isLoading ? (
              <Square className="h-4 w-4 fill-current" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </PromptInputAction>
      </PromptInputActions>
    </PromptInput>
  );
}
