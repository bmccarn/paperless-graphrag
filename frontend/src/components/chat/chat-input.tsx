'use client';

import { useState, useCallback } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useChatStore } from '@/lib/stores';
import { submitQueryStream } from '@/lib/api';
import { toast } from 'sonner';

export function ChatInput() {
  const [input, setInput] = useState('');
  const {
    isLoading,
    selectedMethod,
    communityLevel,
    addMessage,
    setLoading,
    setThinking,
  } = useChatStore();

  const handleSubmit = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
    addMessage({
      role: 'user',
      content: userMessage,
    });

    setLoading(true);
    setThinking({ message: 'Starting...', detail: 'Preparing query' });

    try {
      const response = await submitQueryStream(
        {
          query: userMessage,
          method: selectedMethod,
          community_level: communityLevel,
        },
        (event) => {
          // Update thinking state based on events
          if (event.type === 'status' || event.type === 'thinking') {
            setThinking({
              message: event.message || 'Processing...',
              detail: event.detail,
            });
          }
        }
      );

      addMessage({
        role: 'assistant',
        content: response.response,
        method: selectedMethod,
      });
    } catch (error) {
      toast.error('Failed to get response', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      addMessage({
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
      });
    } finally {
      setLoading(false);
      setThinking(null);
    }
  }, [input, isLoading, selectedMethod, communityLevel, addMessage, setLoading, setThinking]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex gap-3 items-end">
      <Textarea
        placeholder="Ask a question about your documents..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
        className="min-h-[60px] max-h-[200px] resize-none shadow-sm bg-card border-border/50 focus:border-primary/50"
        rows={2}
      />
      <Button
        onClick={handleSubmit}
        disabled={!input.trim() || isLoading}
        size="icon"
        className="h-[60px] w-[60px] shadow-md hover:shadow-lg transition-all"
      >
        {isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Send className="h-5 w-5" />
        )}
      </Button>
    </div>
  );
}
