'use client';

import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { User, Bot, Copy, Check, ExternalLink, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { getEntity } from '@/lib/api';
import type { Message, EntityDetail } from '@/types';

interface MessageItemProps {
  message: Message;
}

// Parse entity references from data citations
function parseDataReferences(content: string): { entities: string[]; sources: string[] } {
  const entities: string[] = [];
  const sources: string[] = [];

  // Match patterns like [Data: Sources (291); Entities (1780, 3514)]
  const dataMatches = content.matchAll(/\[Data:[^\]]*Entities\s*\(([^)]+)\)[^\]]*\]/g);
  for (const match of dataMatches) {
    const entityIds = match[1].split(',').map(s => s.trim());
    entities.push(...entityIds);
  }

  const sourceMatches = content.matchAll(/\[Data:[^\]]*Sources\s*\(([^)]+)\)[^\]]*\]/g);
  for (const match of sourceMatches) {
    const sourceIds = match[1].split(',').map(s => s.trim());
    sources.push(...sourceIds);
  }

  return { entities: [...new Set(entities)], sources: [...new Set(sources)] };
}

// Component to display an entity source with its name
function EntitySourceLink({ entityId }: { entityId: string }) {
  const [entity, setEntity] = useState<EntityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    getEntity(entityId)
      .then((data) => {
        if (!cancelled) setEntity(data);
      })
      .catch(() => {
        // Silently fail - will show ID as fallback
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [entityId]);

  const displayName = entity?.name || entityId;
  const entityType = entity?.type?.toLowerCase();

  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-auto py-1 px-2 text-xs font-normal justify-start gap-1.5 hover:bg-primary/10"
      onClick={() => router.push(`/graph?entity=${encodeURIComponent(entityId)}`)}
    >
      {loading ? (
        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
      ) : (
        <>
          <span className="truncate max-w-[200px]" title={displayName}>
            {displayName}
          </span>
          {entityType && (
            <span className="text-[10px] text-muted-foreground px-1 py-0.5 bg-muted rounded">
              {entityType}
            </span>
          )}
          <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0" />
        </>
      )}
    </Button>
  );
}

// Format the content to improve readability
function formatContent(content: string): string {
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
  const dataRefs = isUser ? { entities: [], sources: [] } : parseDataReferences(message.content);
  const hasDataRefs = dataRefs.entities.length > 0;

  return (
    <div
      className={cn(
        'group flex gap-4 p-4 rounded-lg',
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
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          )}
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-p:my-2 prose-headings:mt-4 prose-headings:mb-2 prose-li:my-1 prose-ul:my-2">
          <ReactMarkdown
            rehypePlugins={[rehypeRaw]}
            components={{
              p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-5 space-y-1 my-3">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1 my-3">{children}</ol>,
              h3: ({ children }) => <h3 className="text-base font-semibold mt-4 mb-2 text-foreground">{children}</h3>,
              strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
            }}
          >
            {formattedContent}
          </ReactMarkdown>
        </div>

        {/* Data Sources Summary */}
        {hasDataRefs && (
          <div className="mt-4 pt-3 border-t border-border/50">
            <div className="space-y-1">
              <span className="text-xs text-muted-foreground">Sources:</span>
              <div className="flex flex-col gap-0.5">
                {dataRefs.entities.slice(0, 6).map((entityId) => (
                  <EntitySourceLink key={entityId} entityId={entityId} />
                ))}
                {dataRefs.entities.length > 6 && (
                  <span className="text-xs text-muted-foreground pl-2">
                    +{dataRefs.entities.length - 6} more sources
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
