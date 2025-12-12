'use client';

import { User, Bot, Copy, Check, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Message,
  MessageAvatar,
  MessageContent,
  MessageActions,
  MessageAction,
} from '@/components/ui/message';
import { SourceDocumentLink } from './source-document-link';
import type { Message as MessageType } from '@/types';

interface MessageItemProps {
  message: MessageType;
}

// Format the content to improve readability
function formatContent(content: string): string {
  if (!content) return '';
  let formatted = content;

  // Convert lines that look like headers (short lines ending with no period, followed by content)
  formatted = formatted.replace(/^([A-Z][^.:\n]{0,50})$/gm, '### $1');

  // Convert "If you want, I can:" followed by items into a list
  formatted = formatted.replace(
    /If you want, I can:\n/gi,
    '\n**If you want, I can:**\n'
  );

  // Convert lines starting with common list patterns
  formatted = formatted.replace(/^(Pull together|Explain what|Suggest questions)/gm, '- $1');

  // Remove verbose data references - they clutter the text
  // We show a summary at the bottom instead
  formatted = formatted.replace(/\s*\[Data:[^\]]+\]/g, '');

  return formatted;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formattedContent = isUser ? message.content : formatContent(message.content);
  const hasSourceDocuments = !isUser && message.sourceDocuments && message.sourceDocuments.length > 0;

  return (
    <Message
      className={cn(
        'p-4 rounded-lg',
        isUser ? 'bg-muted' : 'bg-background'
      )}
    >
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary' : 'bg-secondary'
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-primary-foreground" />
        ) : (
          <Bot className="h-4 w-4 text-secondary-foreground" />
        )}
      </div>

      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">
              {isUser ? 'You' : 'GraphRAG'}
            </span>
            {message.method && (
              <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">
                {message.method}
              </span>
            )}
          </div>
          {!isUser && (
            <MessageActions className="opacity-0 group-hover:opacity-100 transition-opacity">
              <MessageAction tooltip="Copy">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-green-500" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </Button>
              </MessageAction>
            </MessageActions>
          )}
        </div>

        <MessageContent
          markdown
          className="bg-transparent p-0 prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-p:my-2 prose-headings:mt-4 prose-headings:mb-2 prose-li:my-1 prose-ul:my-2"
        >
          {formattedContent}
        </MessageContent>

        {/* Source Documents - Inline like graph sidebar */}
        {hasSourceDocuments && (
          <div className="mt-4 pt-3 border-t border-border/50">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">
                Source Documents ({message.sourceDocuments!.length})
              </span>
            </div>
            <div className="space-y-1">
              {message.sourceDocuments!.slice(0, 5).map((doc) => (
                <SourceDocumentLink key={doc.paperless_id} document={doc} />
              ))}
              {message.sourceDocuments!.length > 5 && (
                <span className="text-xs text-muted-foreground pl-2 block">
                  +{message.sourceDocuments!.length - 5} more documents
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </Message>
  );
}
