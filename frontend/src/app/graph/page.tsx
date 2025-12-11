'use client';

import { ReactFlowProvider } from '@xyflow/react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { GraphContainer } from '@/components/graph';
import { Loader2 } from 'lucide-react';

function GraphContent() {
  const searchParams = useSearchParams();
  const entityId = searchParams.get('entity') || undefined;

  return (
    <ReactFlowProvider>
      <GraphContainer focusEntityId={entityId} />
    </ReactFlowProvider>
  );
}

export default function GraphPage() {
  return (
    <div className="h-[calc(100vh-9rem)]">
      <div className="mb-6 space-y-2">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
          Knowledge Graph
        </h1>
        <p className="text-muted-foreground text-lg">
          Explore entities and relationships extracted from your documents
        </p>
      </div>

      <div className="h-[calc(100%-5rem)] border border-border/50 rounded-xl overflow-hidden shadow-lg bg-card">
        <Suspense fallback={
          <div className="h-full flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        }>
          <GraphContent />
        </Suspense>
      </div>
    </div>
  );
}
