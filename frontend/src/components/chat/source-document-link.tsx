'use client';

import { FileText, ExternalLink, Network } from 'lucide-react';
import { useRouter } from 'next/navigation';
import type { SourceDocumentRef } from '@/types';

interface SourceDocumentLinkProps {
  document: SourceDocumentRef;
}

export function SourceDocumentLink({ document }: SourceDocumentLinkProps) {
  const router = useRouter();

  const handleNavigateToGraph = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Navigate to graph with document filter
    router.push(`/graph?document=${document.paperless_id}`);
  };

  return (
    <div className="flex items-center gap-2 p-2 rounded bg-muted hover:bg-muted/80 transition-colors group">
      <a
        href={document.view_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 flex-1 min-w-0"
      >
        <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
        <span className="text-sm flex-1 truncate" title={document.title}>
          {document.title}
        </span>
        <ExternalLink className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
      </a>
      <button
        onClick={handleNavigateToGraph}
        className="p-1 rounded hover:bg-background/50 opacity-0 group-hover:opacity-100 transition-opacity"
        title="View in Graph"
      >
        <Network className="h-3 w-3 text-muted-foreground" />
      </button>
    </div>
  );
}
